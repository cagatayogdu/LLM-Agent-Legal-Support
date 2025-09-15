function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToArrayBuffer(base64) {
    const binary_string = atob(base64);
    const len = binary_string.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary_string.charCodeAt(i);
    }
    return bytes.buffer;
}

function convertPemToBinary(pem) {
    const lines = pem.split('\n');
    let base64 = '';
    for (let i = 0; i < lines.length; i++) {
        if (lines[i].trim().length > 0 && 
            !lines[i].includes('-----BEGIN PUBLIC KEY-----') && 
            !lines[i].includes('-----END PUBLIC KEY-----')) {
            base64 += lines[i].trim();
        }
    }
    return base64ToArrayBuffer(base64);
}

class SecureCommunication {
    constructor() {
        this.serverPublicKey = null;
        this.sessionId = null;
        this.aesKey = null;
        this.aesIv = null;
        this.isInitialized = false;
    }

    async initialize() {
        try {
            const response = await fetch('/api/get_public_key');
            if (!response.ok) {
                throw new Error('Failed to get server public key');
            }
            
            const data = await response.json();
            this.serverPublicKey = data.public_key;
            this.sessionId = data.session_id;
            
            const aesKey = await window.crypto.subtle.generateKey(
                {
                    name: "AES-CBC",
                    length: 256
                },
                true,
                ["encrypt", "decrypt"]
            );
            
            const rawKey = await window.crypto.subtle.exportKey("raw", aesKey);
            
            this.aesIv = window.crypto.getRandomValues(new Uint8Array(16));
            
            const aesKeyBase64 = arrayBufferToBase64(rawKey);
            const aesIvBase64 = arrayBufferToBase64(this.aesIv);
            
            const importedPublicKey = await window.crypto.subtle.importKey(
                "spki",
                convertPemToBinary(this.serverPublicKey),
                {
                    name: "RSA-OAEP",
                    hash: "SHA-256"
                },
                false,
                ["encrypt"]
            );
            
            const encryptedKeyBuffer = await window.crypto.subtle.encrypt(
                {
                    name: "RSA-OAEP"
                },
                importedPublicKey,
                new TextEncoder().encode(JSON.stringify({
                    key: aesKeyBase64,
                    iv: aesIvBase64
                }))
            );
            
            const encryptedKeyBase64 = arrayBufferToBase64(encryptedKeyBuffer);
            
            const keyResponse = await fetch('/api/exchange_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    encrypted_key: encryptedKeyBase64,
                    session_id: this.sessionId
                })
            });
            
            if (!keyResponse.ok) {
                throw new Error('Failed to exchange encryption key with server');
            }
            
            this.aesKey = aesKey;
            this.isInitialized = true;
            localStorage.setItem('aesKey', aesKeyBase64);
            localStorage.setItem('aesIv', aesIvBase64);
            return true;
        } catch (error) {
            console.error('Encryption initialization failed:', error);
            return false;
        }
    }

    async encryptData(data) {
        if (!this.isInitialized) {
            throw new Error('Secure communication not initialized');
        }

        try {
            const dataString = typeof data === 'object' ? JSON.stringify(data) : data;
            
            const encryptedData = await window.crypto.subtle.encrypt(
                {
                    name: "AES-CBC",
                    iv: this.aesIv
                },
                this.aesKey,
                new TextEncoder().encode(dataString)
            );
            
            return arrayBufferToBase64(encryptedData);
        } catch (error) {
            console.error('Encryption failed:', error);
            throw error;
        }
    }

    async decryptData(encryptedBase64) {
        if (!this.isInitialized) {
            throw new Error('Secure communication not initialized');
        }

        try {
            const encryptedData = base64ToArrayBuffer(encryptedBase64);
            
            const decryptedData = await window.crypto.subtle.decrypt(
                {
                    name: "AES-CBC",
                    iv: this.aesIv
                },
                this.aesKey,
                encryptedData
            );
            
            const decryptedString = new TextDecoder().decode(decryptedData);
            
            try {
                return JSON.parse(decryptedString);
            } catch (e) {
                return decryptedString;
            }
        } catch (error) {
            console.error('Decryption failed:', error);
            throw error;
        }
    }
}

const secureCommunication = new SecureCommunication(); 