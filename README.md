# LawLMMAgents - Gelişmiş Hukuki Analiz Sistemi

<p align="center">
  <img width="800" height="600" alt="image" src="https://github.com/user-attachments/assets/4525c28c-525f-499a-bab7-ba0b649ad145" />
</p>

## 📋 Proje Hakkında

Bu proje, LLM tabanlı çoklu ajan mimarisiyle geliştirilmiş Adaptif Hukuki Karar Destek Sistemidir. Sistem, yaklaşık 2.500’den fazla Türk mevzuatı ve Yargıtay kararını içeren özel bir vektör veri tabanı üzerine inşa edilmiş RAG (Retrieval-Augmented Generation) altyapısını kullanır. Hibrit RSA + AES şifreleme ile güvenliği sağlar. En özgün katkısı, düşük güven skoruna sahip analizlerde devreye giren adaptif geri bildirim mekanizmasıdır. Bu yapı, sistemin kendi çıktısını eleştirip eksiklikleri tespit ederek yeniden analiz döngüsü başlatmasını sağlar. Böylece yalnızca bilgiye erişim aracı değil, öğrenebilen, eleştirel düşünme yeteneğine sahip bir dijital hukuk danışmanı olarak konumlanır

### 🚀 Projenin Yenilikçi Yaklaşımı

Bu proje, hukuki analiz alanında **ilk defa multi-agent AI sistemini** kullanarak şu yenilikleri getirmektedir:

- **Uzmanlaşmış AI Ajanları**: Her ajan belirli bir hukuki görevi yerine getiren uzman sistem
- **RAG + Web Araması Hibrit Yaklaşımı**: Hem yerel hukuki veritabanından hem de güncel web kaynaklarından bilgi toplama
- **Adaptif Öğrenme Sistemi**: Düşük güven skorlu analizleri otomatik olarak iyileştiren sistem
- **Türk Hukukuna Özelleştirilmiş**: Yargıtay, Danıştay, AYM kararlarına odaklanan özel sistem
- **End-to-End Güvenlik**: Hassas hukuki veriler için tam şifreleme

### 💡 Sistemin Sağladığı Değer

- Emsal araştırma süresini %80 azaltır
- Kapsamlı hukuki analiz raporları üretir
- Güncel içtihat ve mevzuat değişikliklerini takip eder
- Risk analizi ve alternatif çözüm önerileri sunar
- Hukuki karar verme süreçlerini hızlandırır
- Analiz kalitesini standardize eder
- Hukuki bilgiye erişimi demokratikleştirir
- Maliyet verimliliği sağlar

### 🎯 Temel Özellikler

- **Multi-Agent Yapısı**: Uzmanlaşmış AI ajanları ile derin hukuki analiz
- **RAG (Retrieval-Augmented Generation)**: Geniş hukuki veritabanı ile desteklenmiş analiz
- **Güvenli İletişim**: End-to-end şifreleme ile veri güvenliği
- **Web Arayüzü**: Kullanıcı dostu modern web interface
- **Docker Desteği**: Kolay kurulum ve deployment
- **Gerçek Zamanlı Analiz**: Hızlı ve kapsamlı hukuki değerlendirme

## 🏗️ Sistem Mimarisi

### 🤖 AI Ajan Yapısı

Sistem **5 uzmanlaşmış AI ajanından** oluşur ve her ajan farklı hukuki uzmanlık alanında çalışır:

<p align="center">
  <img width="800" height="477" alt="image" src="https://github.com/user-attachments/assets/0b8015b7-16f0-432e-b3c8-bc4586c77554" />
</p>

#### 1. **Hukuki Metin Açıklayıcı Ajanı**
- Karmaşık hukuki metinleri anlaşılır dile çevirir
- Kritik vaka detaylarını (kişi adları, tutarlar, tarihler) korur
- Problem türü tespiti yapar (miras, sözleşme, iş hukuku vb.)
- Hukuki jargonu basitleştirerek analiz için hazırlar

#### 2. **İçtihat ve Emsal Karar RAG Analiz Ajanı**
- **Qdrant vektör veritabanından** benzer emsal kararları bulur
- Semantic search ile ilgili içtihatları analiz eder
- Yargıtay, Danıştay, AYM kararlarını önceliklendirir
- Her emsal için kapsamlı ve detaylı açıklama üretir

#### 3. **Hukuki Emsal Web Tarama Ajanı**
- **Gerçek zamanlı** güncel mahkeme kararlarını web'den tarar
- Güvenilir hukuki kaynakları (resmi siteler) önceliklendirir
- Son dönem mevzuat değişikliklerini takip eder
- Bulunan bilgilerin güvenilirlik analizini yapar

#### 4. **Hukuki Çelişki Tespit ve Entegrasyon Ajanı**
- RAG ve web arama sonuçlarını **akıllı entegrasyon** ile birleştirir
- Farklı kaynaklar arasındaki çelişkileri tespit eder
- Kapsamlı hukuki strateji ve eylem planı önerir
- Her argüman için kanıta dayalı güven skorları hesaplar

#### 5. **Adaptif Hukuki Optimizasyon Ajanı**
- Düşük güven skorlu analizleri **otomatik yeniden yönlendirir**
- Sistem performansını sürekli iyileştiren **öğrenme algoritması**
- Eksik bilgi alanlarını tespit eder ve araştırma önerileri sunar
- Analiz kalitesini artırmak için veri akışını optimize eder

### RAG Yapısı
<p align="center">
  <img width="794" height="453" alt="image" src="https://github.com/user-attachments/assets/c9b780fc-ae03-46c9-b497-221ecad12d8d" />
</p>

Sistemin bilgi temelini oluşturan vektör veri tabanının hazırlanması süreci, mevzuat.gov.tr adresinden temin edilen yaklaşık 2.500 adet kanun metninin işlenmesiyle başlanmıştır. Bu sürecin genel işleyici şekil’de verilmiştir. Ham PDF belgeleri, doğrudan metin çıkarımına olanak tanıyan PyMuPDF (fitz) kütüphanesi ile işlenildi. Ayrıca, tüm belgelerin içeriklerini teker teker bakamayacağımız için içlerinde taranmış veya resim tabanlı sayfa içeren belgelerde bulanabilir. Bu yüzden, metin kaybını önlemek amacıyla, metin çıkarımının başarısız olduğu durumlarda otomatik olarak devreye giren bir OCR mekanizması entegre edilmiştir. Bu özelleştirilmiş yapıda öncelikle Python da yer alan pdf2image kütüphanesi ile sayfaları görsellere dönüştürülür. Sonrasında PyTesseract motoruyla görseldeki metin verileri çıkartılır. Elde edilen ham metin de ajan için gerekli olmayacak verilerde mevcuttur. Bu nedenle, tasarlanan “clean_legal_text” fonksiyonu aracılığıyla sayfa numaraları, tekrar eden başlıklar, satır sonu karakterleri ve diğer dijital yapaylardan arındırılarak temizlenmiştir.

## 🛠️ Teknoloji Stack'i

<p align="center">
  <img width="800" height="400" alt="image" src="https://github.com/user-attachments/assets/af0d163f-5be6-43bf-9230-2317e89d4439" />
</p>

### Backend
- **Python 3.12**: Ana programlama dili
- **CrewAI**: Multi-agent AI framework
- **Flask**: Web framework
- **LangChain**: LLM orchestration
- **Qdrant**: Vektör veritabanı
- **Redis**: Cache ve session management

### AI/ML
- **OpenAI GPT-4**: Ana dil modeli
- **Sentence Transformers**: Embedding modeli
- **HuggingFace**: Model hub
- **PyTorch**: Deep learning framework

### Güvenlik
- **RSA Encryption**: Anahtar değişimi
- **AES-256**: Veri şifreleme
- **Cryptography**: Kriptografik işlemler

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-service orchestration
- **Waitress**: Production WSGI server

## 📦 Kurulum

### Ön Gereksinimler

- Docker ve Docker Compose
- Python 3.12+ (local development için)
- Git

### 🚀 Hızlı Başlangıç (Docker ile)

1. **Repository'yi klonlayın:**
```bash
git clone https://github.com/cagatayogdu/LLM-Agent-Legal-Support.git
cd LLM-Agent-Legal-Support
```

2. **Environment dosyasını oluşturun:**
```bash
cp .env.example .env
```

3. **Environment değişkenlerini düzenleyin:**
```bash
# .env dosyasını açın ve aşağıdaki değerleri girin:
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here
QDRANT_URL=your_qdrant_url_here  # Vector veri tabanı bağlantısı
QDRANT_API_KEY=your_qdrant_api_key_here  # Vector veri tabanı için
```

4. **Docker Compose ile başlatın:**
```bash
docker-compose up -d
```

5. **Sistem hazır! Aşağıdaki URL'den erişin:**
```
http://localhost:5000
```

### 🎯 Tek Komut Kurulum

Bu sistem **tamamen Docker tabanlı** olarak tasarlanmıştır. Manuel kurulum gerekmez!

```bash
# Tek komutla tüm sistemi başlatın
docker-compose up -d

# Sistem durumunu kontrol edin
docker-compose ps

# Logları izleyin
docker-compose logs -f app
```

**Not:** Sistem cloud-based Qdrant kullandığı için yerel Qdrant kurulumu gerekmez.

## 💡 Kullanım

### Web Arayüzü

<p align="center">
  <img width="833" height="418" alt="image" src="https://github.com/user-attachments/assets/fb2f098e-5e49-403f-81d1-02ee2f466470" />
</p>

1. **Ana sayfaya gidin:** `http://localhost:5000`
2. **Hukuki vakayı girin:** Metin alanına vaka detaylarını yazın
3. **Analiz et butonuna tıklayın**
4. **Sonuçları bekleyin:** Sistem kapsamlı analiz gerçekleştirir
5. **Raporu inceleyin:** Detaylı hukuki analiz raporunu görüntüleyin

## 📁 Proje Yapısı

```
LawLMMAgents/
├── app/
│   ├── config/              # Ajan ve task konfigürasyonları
│   │   ├── agents.yaml      # AI ajan tanımları
│   │   └── tasks.yaml       # Görev tanımları
│   ├── crews/               # AI ajan ekipleri
│   │   ├── legal_analysis_crew.py
│   │   ├── legal_feedback_crew.py
│   │   └── legal_input_processing_crew.py
│   ├── db/                  # Veritabanı dosyaları
│   ├── reports/             # Analiz raporları
│   ├── tools/               # AI araçları
│   │   └── qdrant_vector_search_tool.py
│   ├── utils/               # Yardımcı modüller
│   │   ├── crypto_utils.py  # Şifreleme araçları
│   │   └── advanced_report_generator.py
│   ├── vector_db/           # Vektör veritabanı sistemi
│   ├── web/                 # Web arayüzü
│   │   ├── index.html
│   │   ├── scripts.js
│   │   └── crypto.js
│   ├── llms.py             # LLM konfigürasyonları
│   ├── run.py              # Ana uygulama başlatıcı
│   └── web_server.py       # Flask web sunucusu
├── docker-compose.yml      # Docker Compose konfigürasyonu
├── Dockerfile             # Docker image tanımı
├── requirements.txt       # Python bağımlılıkları
└── README.md             # Bu dosya
```

### Ajan Konfigürasyonu

AI ajanları `app/config/agents.yaml` dosyasından konfigüre edilir:

```yaml
legal_text_clarifier:
  role: "Hukuki Metin Açıklayıcı Uzmanı"
  goal: "Karmaşık hukuki metinleri anlaşılır dile çevirme"
  backstory: "Hukuki NLP uzmanı..."
```

## 📈 Performans

- **Analiz Süresi**: Ortalama 2-3 dakika
- **Doğruluk Oranı**: %85+ güven skorlu analizler
- **Veri İşleme**: 10MB+ doküman desteği

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız.

---

**Not**: Bu sistem Türk hukuk sistemi için optimize edilmiştir ve sürekli geliştirilmektedir. Herhangi bir hukuki karar vermeden önce mutlaka uzman hukukçu görüşü alınız.
