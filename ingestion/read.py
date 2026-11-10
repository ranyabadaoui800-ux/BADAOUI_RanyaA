import gzip
import os
import os.path as pt

from logger_config import get_logger

"""
Module ingestion : lit tous les fichiers de logs d'un dossier (.log, .1, .2 et .gz)
in : chemin du dossier data
out : liste de toutes les lignes
"""

logger = get_logger("ingestion")


def read_file(file_path: str) -> list:
    # lit un seul fichier, compresse (.gz) ou non
    try:
        if file_path.endswith(".gz"):
            opener = gzip.open(file_path, mode="rt", encoding="utf-8")
        else:
            opener = open(file_path, mode="r", encoding="utf-8")
        with opener as f:
            lines = f.readlines()
        logger.info(f"{file_path} : {len(lines)} lignes lues")
        return lines
    except PermissionError:
        logger.error(f"Permission refusee pour le fichier {file_path}")
    except gzip.BadGzipFile:
        logger.error(f"Fichier gz corrompu ou invalide : {file_path}")
    except EOFError:
        logger.error(f"Fichier gz incomplet (coupe) : {file_path}")
    except UnicodeDecodeError:
        logger.error(f"Probleme d'encodage (pas UTF-8) dans {file_path}")
    except IsADirectoryError:
        logger.warning(f"{file_path} est un dossier, il est ignore")
    except Exception as e:
        logger.exception(f"Erreur inattendue en lisant {file_path} : {e}")
    return []


def ingest(path: str) -> list:
    rows = []
    try:
        files = sorted(os.listdir(path))
    except FileNotFoundError:
        logger.error(f"Le dossier {path} n'existe pas")
        return rows
    except NotADirectoryError:
        logger.error(f"{path} n'est pas un dossier")
        return rows
    except PermissionError:
        logger.error(f"Permission refusee pour le dossier {path}")
        return rows

    if not files:
        logger.warning(f"Le dossier {path} est vide")
        return rows

    for file in files:
        file_path = pt.join(path, file)
        rows.extend(read_file(file_path))  # on ajoute les lignes de chaque fichier

    logger.info(f"Ingestion terminee : {len(files)} fichiers, {len(rows)} lignes au total")
    return rows


if __name__ == "__main__":
    data = ingest("./data")
    for line in data[:20]:  # affiche les 20 premieres lignes
        print(line.strip())