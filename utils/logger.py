import logging
import os
from logging.handlers import RotatingFileHandler
import datetime

def setup_logger(name, level=logging.INFO, log_to_console=True, log_to_file=True):
    """Configure un logger avec rotation des fichiers"""
    
    # Créer le dossier des logs s'il n'existe pas
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Format du logger
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Créer le logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Éviter les doublons de handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Ajouter un handler pour la console
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Ajouter un handler pour les fichiers avec rotation
    if log_to_file:
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(logs_dir, f'{name}_{today}.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10 Mo
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
