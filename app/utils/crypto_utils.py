import os
import json
import base64
import uuid
import redis
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import logging
from typing import Tuple, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RedisCryptoManager:
    _redis_client: redis.Redis = None
    
    RSA_PRIVATE_KEY_NAME = "crypto:rsa_private_key"
    RSA_PUBLIC_KEY_NAME = "crypto:rsa_public_key"
    AES_KEY_TTL = 3600

    def __init__(self):
        self._get_redis_client()
        self._initialize_rsa_keys()

    def _get_redis_client(self):
        if not RedisCryptoManager._redis_client:
            try:
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", 6379))
                logger.info(f"Redis bağlantısı kuruluyor: {redis_host}:{redis_port}")
                RedisCryptoManager._redis_client = redis.Redis(
                    host=redis_host, 
                    port=redis_port, 
                    decode_responses=True
                )
                RedisCryptoManager._redis_client.ping()
                logger.info("Redis bağlantısı başarılı.")
            except redis.exceptions.ConnectionError as e:
                logger.error(f"Redis bağlantısı kurulamadı: {e}", exc_info=True)
                RedisCryptoManager._redis_client = None
        return RedisCryptoManager._redis_client

    def _initialize_rsa_keys(self, force_new=False):
        r = self._get_redis_client()
        if not r:
            logger.error("RSA anahtarı oluşturulamadı çünkü Redis bağlantısı kurulamadı.")
            return

        if force_new or not r.exists(self.RSA_PRIVATE_KEY_NAME):
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')

            r.set(self.RSA_PRIVATE_KEY_NAME, private_pem)
            r.set(self.RSA_PUBLIC_KEY_NAME, public_pem)
            logger.info("Redis'e RSA anahtarı başarıyla kaydedildi.")

    def get_public_key_and_session(self) -> Tuple[str, str]:
        r = self._get_redis_client()
        if not r: return None, None

        public_key_pem = r.get(self.RSA_PUBLIC_KEY_NAME)
        if not public_key_pem:
            logger.error("RSA public key Redis'te bulunamadı.")
            return None, None
            
        session_id = str(uuid.uuid4())
        return public_key_pem, session_id

    def store_and_decrypt_aes_key(self, encrypted_key_base64: str, session_id: str) -> bool:
        r = self._get_redis_client()
        if not r: return False

        try:
            private_key_pem = r.get(self.RSA_PRIVATE_KEY_NAME)
            if not private_key_pem:
                logger.error("RSA private key Redis'te bulunamadı.")
                return False

            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            encrypted_key = base64.b64decode(encrypted_key_base64)
            decrypted_bytes = private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            key_data = json.loads(decrypted_bytes.decode('utf-8'))
            
            r.set(f"aes_key:{session_id}", key_data['key'], ex=self.AES_KEY_TTL)
            r.set(f"aes_iv:{session_id}", key_data['iv'], ex=self.AES_KEY_TTL)
            
            logger.info(f"Başarıyla AES anahtarı çözüldü ve Redis'e kaydedildi: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Hata: {session_id}: {e}", exc_info=True)
            return False

    def _get_aes_cipher(self, session_id: str):
        r = self._get_redis_client()
        if not r: return None

        key_b64 = r.get(f"aes_key:{session_id}")
        iv_b64 = r.get(f"aes_iv:{session_id}")
        
        if not key_b64 or not iv_b64:
            logger.error(f"Redis for session: {session_id}")
            return None
            
        aes_key = base64.b64decode(key_b64)
        aes_iv = base64.b64decode(iv_b64)
        
        return Cipher(
            algorithms.AES(aes_key),
            modes.CBC(aes_iv),
            backend=default_backend()
        )

    def encrypt_data(self, data: Any, session_id: str) -> str:
        cipher = self._get_aes_cipher(session_id)
        if not cipher:
            raise ValueError(f"AES şifreleme cipher'ı {session_id}: {session_id}")
        
        if isinstance(data, (dict, list)):
            data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        else:
            data_bytes = str(data).encode('utf-8')
        
        encryptor = cipher.encryptor()
        padded_data = self._pkcs7_pad(data_bytes)
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data(self, encrypted_data_base64: str, session_id: str) -> Any:
        cipher = self._get_aes_cipher(session_id)
        if not cipher:
            raise ValueError(f"AES cipher for session: {session_id}")
        
        encrypted_data = base64.b64decode(encrypted_data_base64)
        decryptor = cipher.decryptor()
        
        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadded_data = self._pkcs7_unpad(decrypted_padded_data).decode('utf-8')
        
        try:
            return json.loads(unpadded_data)
        except json.JSONDecodeError:
            return unpadded_data
    
    def _pkcs7_pad(self, data: bytes) -> bytes:
        block_size = algorithms.AES.block_size // 8
        padding_size = block_size - (len(data) % block_size)
        padding = bytes([padding_size] * padding_size)
        return data + padding
    
    def _pkcs7_unpad(self, data: bytes) -> bytes:
        padding_size = data[-1]
        if padding_size > algorithms.AES.block_size // 8 or padding_size == 0:
            raise ValueError("Invalid padding")
        if data[-padding_size:] != bytes([padding_size] * padding_size):
            raise ValueError("Invalid padding bytes")
        return data[:-padding_size]

crypto_manager = RedisCryptoManager() 