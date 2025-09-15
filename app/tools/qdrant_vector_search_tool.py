import os
import re
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

import torch
from dotenv import load_dotenv
from pydantic import Field, PrivateAttr
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny, Range
from qdrant_client.http.exceptions import UnexpectedResponse
from langchain_huggingface import HuggingFaceEmbeddings
from crewai_tools import RagTool
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

_global_embedding_model: Optional[HuggingFaceEmbeddings] = None
_global_qdrant_client: Optional[QdrantClient] = None

class QdrantLegalSearchTool(RagTool):
    #Burada ajanın bu toolsu kullanmadan önce ne olduğunu, ne işe yaradığını, nasıl kullanılacağını, ne gibi sonuçlar döndüreceğini yazıyoruz.
    #Ajan bu sayede toolsu öğrenmiş olacak.
    name: str = "Gelişmiş Hukuki Bilgi Arama Aracı"
    description: str = "Anlamsal embedding'ler ve metadata filtreleri kullanarak Qdrant üzerinde gelişmiş hukuki belge araması yapar."
    
    _embedding_model: PrivateAttr
    _client: PrivateAttr
    _connection_initialized: PrivateAttr = False
    
    collection_name: str = Field(
        default=os.getenv("QDRANT_COLLECTION_NAME", "turkiye_hukuk_dokumanlari_v3"),
        description="Qdrant collection adı."
    )
    base_similarity_threshold: float = Field(
        default=0.6,
        description="Arama sonuçları için temel benzerlik eşiği."
    )
    min_similarity_threshold: float = Field(
        default=0.5,
        description="İzin verilen minimum benzerlik eşiği (fallback durumunda kullanılır)."
    )
    max_results: int = Field(
        default=5,
        description="Döndürülecek maksimum sonuç sayısı."
    )
    auto_fallback: bool = Field(
        default=True,
        description="Sonuç bulunamazsa otomatik olarak geri çekilme stratejilerinin denenip denenmeyeceği."
    )
    
    _legal_areas_mapping: Dict[str, List[str]] = {
        'ticaret_hukuku': ['ticaret', 'şirket', 'anonim', 'limited', 'ortaklık', 'tacir', 'ttk'],
        'medeni_hukuk': ['medeni', 'aile', 'miras', 'eşya', 'kişiler', 'mk', 'boşanma', 'velayet', 'tenkis'],
        'ceza_hukuku': ['ceza', 'suç', 'mahkumiyet', 'beraat', 'sanık', 'tck', 'hapis', 'kaza'],
        'idare_hukuku': ['idare', 'kamu', 'devlet', 'memur', 'disiplin', 'atama'],
        'is_hukuku': ['iş', 'çalışma', 'işçi', 'işveren', 'sendika', 'iş sözleşmesi'],
        'vergi_hukuku': ['vergi', 'gelir', 'kurumlar', 'kdv', 'stopaj', 'beyanname', 'matrah'],
        'icra_iflas_hukuku': ['icra', 'iflas', 'konkordato', 'haciz', 'alacak', 'borçlu'],
        'anayasa_hukuku': ['anayasa', 'temel hak', 'özgürlük', 'cumhurbaşkanı', 'meclis']
    }
    
    _common_legal_keywords: List[str] = [
        'madde', 'kanun', 'yönetmelik', 'tüzük', 'kararnâme', 'genelge', 'hüküm', 'fıkra',
        'mahkeme', 'dava', 'karar', 'hakkında', 'dair', 'ilişkin', 'ceza', 'hukuk', 'medeni',
        'ticaret', 'vergi', 'taraf', 'davacı', 'davalı', 'sanık', 'suç', 'beraat', 'mahkumiyet',
        'tazminat', 'yargıtay', 'danıştay', 'anayasa', 'borçlar', 'miras', 'aile', 'eşya',
        'iş', 'sosyal güvenlik', 'idare', 'icra', 'iflas', 'noter', 'avukat', 'hakim', 'savcı'
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initialize_client()
        self._initialize_embedding_model()

    def _initialize_client(self) -> None:
        global _global_qdrant_client
        if _global_qdrant_client and self._client_is_healthy(_global_qdrant_client):
            self._client = _global_qdrant_client
            self._connection_initialized = True
            logger.info("Mevcut Qdrant istemcisi yeniden kullanılıyor.")
            return
        
        try:
            qdrant_url = os.getenv("QDRANT_URL")
            qdrant_api_key = os.getenv("QDRANT_API_KEY")
            if not qdrant_url:
                logger.error("QDRANT_URL ortam değişkeni ayarlanmamış. Qdrant bağlantısı kurulamıyor.")
                self._connection_initialized = False
                return

            self._client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                prefer_grpc=True,
                timeout=20.0, 
            )
            self._client.get_collections()
            _global_qdrant_client = self._client
            self._connection_initialized = True
            logger.info(f"Qdrant'a yeni bir bağlantı kuruldu ve global olarak ayarlandı.")
        except Exception as e:
            logger.error(f"Qdrant client başlatılamadı: {e}", exc_info=True)
            self._connection_initialized = False
            _global_qdrant_client = None

    def _client_is_healthy(self, client: QdrantClient) -> bool:
        try:
            client.get_collections()
            return True
        except Exception:
            logger.warning("Mevcut Qdrant istemci bağlantısı sağlıksız. Yeniden bağlanılacak.")
            return False

    def _initialize_embedding_model(self) -> None:
        global _global_embedding_model
        if _global_embedding_model:
            self._embedding_model = _global_embedding_model
            logger.info("Mevcut embedding modeli yeniden kullanılıyor.")
            return

        try:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Embedding modeli için '{device}' cihazı kullanılacak. Bu işlem biraz zaman alabilir...")
            self._embedding_model = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )
            _global_embedding_model = self._embedding_model
            logger.info("Çok dilli embedding modeli başarıyla yüklendi ve global olarak ayarlandı.")
        except Exception as e:
            logger.error(f"Embedding modeli başlatılamadı: {e}", exc_info=True)
            raise
    #Burada ajan toolsu kullanırken problemle karşılaştırsa tekrar şansını deneme hakkı veriyoruz
    #Çünkü bazı dil modelleri toolsu kullanırken problemle karşılaşabilir. Hata oluşursa hatasından ders çıkarıyor,
    #Tekrar doğrusunu bulup denediği oluyor.
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10), 
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((UnexpectedResponse, ConnectionError)),
        reraise=True
    )
    def _run(
        self, 
        query: str, 
        filter: Optional[Union[Filter, Dict[str, Any]]] = None, 
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict]:
        if not self._connection_initialized:
            logger.warning("Qdrant bağlantısı hazır değil. Servis çağrılamıyor.")
            return [{"error": "Qdrant bağlantısı kurulamadı.", "query": query}]
        
        if isinstance(filter, dict) and filter:
            filter = self._parse_filter_dict(filter)
        
        search_limit = limit if limit is not None else self.max_results
        
        # 1. Ana Arama
        threshold = score_threshold if score_threshold is not None else self.base_similarity_threshold
        results = self._execute_search(query, filter, threshold, search_limit)
        
        if results or not self.auto_fallback:
            return results

        # Fallback Stratejileri 
        logger.info(f"'{query}' için '{threshold}' eşiğiyle sonuç bulunamadı. Fallback stratejileri deneniyor.")
        
        # Fallback 1: Eşik değerini düşür
        lower_threshold = max(threshold - 0.1, self.min_similarity_threshold) 
        logger.info(f"Fallback 1: Benzerlik eşiği {lower_threshold}'e düşürülüyor.")
        results = self._execute_search(query, filter, lower_threshold, search_limit)
        if results:
            return results
        
        # Fallback 2: Sorgudan anahtar kelimeler çıkararak ara
        keyword_query = self._extract_keywords_for_fallback(query)
        if keyword_query.strip() and keyword_query != query:
            logger.info(f"Fallback 2: Sorgu anahtar kelimelere indirgendi -> '{keyword_query}'")
            results = self._execute_search(keyword_query, filter, threshold, search_limit)
            if results:
                return results
        
        logger.info(f"Tüm fallback stratejileri denendi ancak '{query}' için sonuç bulunamadı.")
        return []

    def _execute_search(
        self, 
        query: str, 
        filter: Optional[Filter], 
        threshold: float,
        limit: int
    ) -> List[Dict]:
        try:
            cleaned_query = self._preprocess_query(query)
            if not cleaned_query:
                logger.warning(f"Ön işleme sonrası sorgu boş. Orijinal sorgu: '{query}'")
                return []

            query_embedding = self._embedding_model.embed_query(cleaned_query)
       
            search_result = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=filter,
                limit=limit,
                with_payload=True,
                score_threshold=threshold
            )
            
            results = [self._format_hit(hit) for hit in search_result if hit.payload and hit.payload.get("text")]
            
            logger.info(f"Sorgu '{cleaned_query[:50]}...' için {threshold} eşiğiyle {len(results)} sonuç bulundu.")
            return results

        except Exception as e:
            logger.error(f"Arama sırasında hata oluştu. Sorgu: '{query}'. Hata: {str(e)}", exc_info=True)
            return []

    def _format_hit(self, hit) -> Dict:
        payload = hit.payload
        metadata = {
            "kaynak_dosya": payload.get("dosya_adi", "bilinmiyor"),
            "dokuman_tipi": payload.get("dokuman_tipi", "bilinmiyor"),
            "ana_hukuk_alani": payload.get("ana_hukuk_alani", "bilinmiyor"),
            "konular": payload.get("hakkinda_konu", ""),
            "etiketler": payload.get("etiket", ""),
            "madde_numaralari": payload.get("madde_no", ""),
            "kanun_referanslari": payload.get("kanun_referanslari", ""),
            "chunk_index": payload.get("chunk_index", -1),
            "qdrant_id": str(hit.id)
        }
        return {
            "text": payload.get("text", ""),
            "score": hit.score,
            "metadata": metadata
        }

    def _preprocess_query(self, query: str) -> str:
        query = query.lower().strip()
        
        abbreviations = {
            'ttk': 'türk ticaret kanunu', 'tck': 'türk ceza kanunu', 'mk': 'medeni kanun',
            'iik': 'icra iflas kanunu', 'vuk': 'vergi usul kanunu', 'hmk': 'hukuk muhakemeleri kanunu',
            'aym': 'anayasa mahkemesi', 'md': 'madde'
        }
        
        for abbr, full in abbreviations.items():
            query = re.sub(r'\b' + re.escape(abbr) + r'\b', full, query)
        
        return query

    def _extract_keywords_for_fallback(self, query: str) -> str:
        lower_query = query.lower()
        concepts = set()

        # 1. Hukuk alanlarını tespit et
        for area, keywords in self._legal_areas_mapping.items():
            if any(keyword in lower_query for keyword in keywords):
                concepts.add(area.replace("_", " "))
        
        # 2. Spesifik hukuki terimleri ve madde numaralarını bul
        article_match = re.search(r'(madde|md\.?)\s*(\d+)', lower_query)
        if article_match:
            concepts.add(f"madde {article_match.group(2)}")

        for term in self._common_legal_keywords:
            if term in lower_query:
                concepts.add(term)
        
        # Yeterli konsept bulunamazsa orijinal sorguyu koru
        if len(concepts) < 2:
            return query

        return " ".join(sorted(list(concepts), key=len, reverse=True))

    def _parse_filter_dict(self, filter_dict: Dict[str, Any]) -> Filter:
        must_conditions = []
        for key, value in filter_dict.items():
            if isinstance(value, list):
                condition = FieldCondition(key=key, match=MatchAny(any=value))
            elif isinstance(value, dict) and ('gte' in value or 'lte' in value):
                condition = FieldCondition(key=key, range=Range(**value))
            else:
                condition = FieldCondition(key=key, match=MatchValue(value=value))
            must_conditions.append(condition)
        
        return Filter(must=must_conditions) if must_conditions else None

    def search_by_legal_area(self, query: str, legal_area: str, limit: int = 3) -> List[Dict]:
        logger.info(f"Hukuk alanına göre arama: Alan='{legal_area}', Sorgu='{query[:50]}...'")
        qdrant_filter = self._parse_filter_dict({"ana_hukuk_alani": legal_area})
        return self._run(query=query, filter=qdrant_filter, limit=limit)

    def search_by_article(self, query: str, article_numbers: List[str], limit: int = 3) -> List[Dict]:
        logger.info(f"Madde numarasına göre arama: Maddeler='{article_numbers}', Sorgu='{query[:50]}...'")
        qdrant_filter = self._parse_filter_dict({"madde_numaralari": article_numbers})
        return self._run(query=query, filter=qdrant_filter, limit=limit)

    def search_by_document_type(self, query: str, document_type: str, limit: int = 3) -> List[Dict]:
        logger.info(f"Doküman tipine göre arama: Tip='{document_type}', Sorgu='{query[:50]}...'")
        qdrant_filter = self._parse_filter_dict({"dokuman_tipi": document_type})
        return self._run(query=query, filter=qdrant_filter, limit=limit)

    def hybrid_search(
        self, 
        query: str, 
        legal_area: Optional[str] = None,
        document_type: Optional[str] = None,
        article_numbers: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        filters = {}
        if legal_area:
            filters["ana_hukuk_alani"] = legal_area
        if document_type:
            filters["dokuman_tipi"] = document_type
        if article_numbers:
            filters["madde_numaralari"] = article_numbers

        logger.info(f"Hibrit arama: Filtreler='{filters}', Sorgu='{query[:50]}...'")
        qdrant_filter = self._parse_filter_dict(filters) if filters else None
        return self._run(query=query, filter=qdrant_filter, limit=limit)