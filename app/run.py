import os
from web_server import app
from waitress import serve
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"Waitress üretim sunucusu başlatılıyor...")
    logger.info(f"Uygulama http://{host}:{port} adresinde hizmet verecek.")
    
    serve(app, host=host, port=port, threads=2) 