import sys
import os
import traceback
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.crypto_utils import crypto_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)

confidence_threshold = 0.80
max_iterations = 3

legal_input_processor = None
legal_analysis_processor = None
legal_feedback_processor = None
feedback = None
report_generator = None
llm_crews_initialized = False

def initialize_llm_crews():
    from crews.legal_input_processing_crew import LegalInputProcessingCrew
    from crews.legal_analysis_crew import LegalAnalysisProcessingCrew
    from crews.legal_feedback_crew import LegalFeedbackCrew
    from crews.feedback import Feedback
    from utils.advanced_report_generator import AdvancedLegalReportGenerator

    try:
        local_legal_input_processor = LegalInputProcessingCrew().crew()
        local_legal_analysis_processor = LegalAnalysisProcessingCrew().crew()
        local_legal_feedback_processor = LegalFeedbackCrew().crew()
        local_feedback = Feedback(local_legal_analysis_processor, local_legal_feedback_processor, max_iterations)
        local_report_generator = AdvancedLegalReportGenerator(confidence_threshold, max_iterations)
        
        logger.info("[SYSTEM] LLM ekipleri başarıyla başlatıldı.")

        return local_legal_input_processor, local_legal_analysis_processor, local_legal_feedback_processor, local_feedback, local_report_generator
    except Exception as e:
        logger.error(f"[SYSTEM] LLM ekipleri başlatılırken hata: {str(e)}", exc_info=True)
        raise e

def lazy_initialize_llm_crews():
    global legal_input_processor, legal_analysis_processor, legal_feedback_processor, feedback, report_generator, llm_crews_initialized
    
    if llm_crews_initialized:
        return

    logger.info("[SYSTEM] LLM ekipleri başlatılıyor...")
    try:
        (
            legal_input_processor,
            legal_analysis_processor,
            legal_feedback_processor,
            feedback,
            report_generator,
        ) = initialize_llm_crews()
        llm_crews_initialized = True
    except Exception as e:
        logger.error(f"[SYSTEM] Tembel başlatma sırasında LLMler yüklenemedi: {str(e)}", exc_info=True)

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/api/get_public_key')
def get_public_key():
    try:
        public_key, session_id = crypto_manager.get_public_key_and_session()
        if not public_key or not session_id:
            return jsonify({'error': 'Sunucu anahtar çifti alınamadı.'}), 500
        logger.info(f"Yeni oturum için public key gönderildi: {session_id}")
        return jsonify({'public_key': public_key, 'session_id': session_id})
    except Exception as e:
        logger.error(f"Public key alınırken hata oluştu: {str(e)}", exc_info=True)
        return jsonify({'error': "Sunucuda bir hata oluştu."}), 500

@app.route('/api/exchange_key', methods=['POST'])
def exchange_key():
    try:
        data = request.get_json()
        encrypted_key = data.get('encrypted_key')
        session_id = data.get('session_id')
        
        if not all([encrypted_key, session_id]):
            return jsonify({'error': 'Eksik parametre: encrypted_key ve session_id zorunludur.'}), 400
        
        success = crypto_manager.store_and_decrypt_aes_key(encrypted_key, session_id)
        if not success:
            return jsonify({'error': 'AES anahtarı çözülemedi veya saklanamadı.'}), 500
        
        logger.info(f"Oturum için anahtar değişimi başarılı: {session_id}")
        return jsonify({'status': 'success', 'message': 'Anahtar degisimi basarili'})
    except Exception as e:
        logger.error(f"Anahtar değişimi sırasında hata: {str(e)}", exc_info=True)
        return jsonify({'error': "Sunucuda bir hata oluştu."}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_legal_case():
    lazy_initialize_llm_crews()

    if not legal_input_processor:
        return jsonify({'error': 'Analiz servisi şu anda mevcut değil. Lütfen daha sonra tekrar deneyin.'}), 503

    try:
        data = request.get_json()
        encrypted_data = data.get('encrypted_data')
        session_id = data.get('session_id')

        if encrypted_data:
            if not session_id:
                return jsonify({'error': 'Şifreli istekler için session_id zorunludur.'}), 400
            try:
                decrypted_data = crypto_manager.decrypt_data(encrypted_data, session_id)
                legal_case_input = decrypted_data.get('legal_case', '')
            except Exception as e:
                logger.error(f"Şifre çözme hatası. Oturum: {session_id}, Hata: {str(e)}", exc_info=True)
                return jsonify({'error': 'Veri şifresi çözülemedi. Oturum zaman aşımına uğramış olabilir.'}), 400
        else:
            legal_case_input = data.get('legal_case', '')
        
        if not legal_case_input:
            return jsonify({'error': 'legal_case verisi zorunludur.'}), 400

        logger.info(f"[SERVER] LLM analizi başlatılıyor. Oturum: {session_id}")
        logger.info(f"[SERVER] Analiz edilen vaka (ilk 100 karakter): {legal_case_input[:100]}...")

        processed_legal_data = legal_input_processor.kickoff(
            inputs={'topic': legal_case_input}
        )
        
        if hasattr(processed_legal_data, "model_dump"):
            processed_legal_data = processed_legal_data.model_dump()
          
        legal_analysis_data = feedback.process_feedback(processed_legal_data, confidence_threshold)
        
        if hasattr(legal_analysis_data, "model_dump"):
            legal_analysis_data = legal_analysis_data.model_dump()

        optimized_report = report_generator.generate_optimized_report(legal_analysis_data)
        optimized_report["input_text"] = legal_case_input
        
        json_filename = report_generator.save_report(optimized_report)
        logger.info(f"[SERVER] Rapor kaydedildi: {json_filename}")
        
        if encrypted_data:
            try:
                encrypted_response = crypto_manager.encrypt_data(optimized_report, session_id)
                return jsonify({'encrypted_data': encrypted_response})
            except Exception as e:
                logger.error(f"Yanıt şifreleme hatası. Oturum: {session_id}, Hata: {str(e)}", exc_info=True)
                return jsonify({'error': 'Yanıt şifrelenirken bir hata oluştu.'}), 500
        else:
            return jsonify(optimized_report)
        
    except Exception as e:
        logger.error(f"Hukuki analiz sırasında beklenmedik hata: {str(e)}", exc_info=True)
        traceback.print_exc()
        return jsonify({'error': 'Analiz sırasında sunucuda beklenmedik bir hata oluştu.'}), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'Hukuki Analiz Sistemi çalışıyor',
        'version': '3.0.0'
    })

if __name__ == "__main__":
    logger.info("Flask geliştirme sunucusu başlatılıyor...")
    app.run(host='0.0.0.0', port=5000, debug=False)