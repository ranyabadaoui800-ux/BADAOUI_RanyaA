import csv
import os

from logger_config import get_logger

"""
Module storage : enregistre les evenements extraits dans un fichier CSV
et permet de les relire pour le dashboard.
"""

logger = get_logger("storage")

OUTPUT_DIR = "output"
CSV_FILE = os.path.join(OUTPUT_DIR, "events.csv")
COLUMNS = ["month", "day", "time", "user", "ip", "country", "status", "invalid_user"]


def save_events(events: list, path: str = CSV_FILE) -> bool:
    if not events:
        logger.warning("Aucun evenement a enregistrer")
        return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(events)
        logger.info(f"{len(events)} evenements enregistres dans {path}")
        return True
    except PermissionError:
        logger.error(f"Permission refusee pour ecrire {path}")
    except ValueError as e:
        logger.error(f"Colonne inattendue dans les donnees : {e}")
    except OSError as e:
        logger.error(f"Erreur d'ecriture de {path} : {e}")
    return False


def load_events(path: str = CSV_FILE) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            events = list(csv.DictReader(f))
        for e in events:
            e["invalid_user"] = e["invalid_user"] == "True"  # le CSV stocke du texte
        logger.info(f"{len(events)} evenements charges depuis {path}")
        return events
    except FileNotFoundError:
        logger.error(f"Le fichier {path} n'existe pas, lancez d'abord le pipeline")
    except KeyError as e:
        logger.error(f"Colonne manquante dans {path} : {e}")
    except OSError as e:
        logger.error(f"Erreur de lecture de {path} : {e}")
    return []