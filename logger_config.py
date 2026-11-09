import logging
import os
from logging.handlers import TimedRotatingFileHandler

"""
Configuration du logging du projet.
Chaque module a son propre fichier de log dans le dossier logs/ :
    logs/ingestion.log, logs/processing.log, logs/storage.log, logs/serving.log, logs/main.log
Les fichiers tournent chaque jour (rotation par periode) et on garde 7 jours.
"""

LOG_DIR = "logs"
FORMAT = "%(asctime)s|%(name)s|%(levelname)s|%(message)s"
DATE_FORMAT = "%d/%m/%Y %H:%M:%S"


def get_logger(module_name: str) -> logging.Logger:
    # module_name : nom du module (ex: "ingestion") -> donne le nom du fichier de log
    logger = logging.getLogger(module_name)

    # eviter d'ajouter les handlers deux fois si on appelle la fonction plusieurs fois
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    os.makedirs(LOG_DIR, exist_ok=True)
    formatter = logging.Formatter(FORMAT, datefmt=DATE_FORMAT)

    # fichier de log du module, rotation chaque jour a minuit
    file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, module_name + ".log"),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # affichage console : seulement INFO et plus
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger