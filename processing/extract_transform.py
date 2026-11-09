import re

from logger_config import get_logger

"""
Module processing : extrait les informations utiles des lignes de logs avec des regex
et les transforme en dictionnaires.

Lignes qui nous interessent :
  Failed password for root from 45.148.10.147 port 8868 ssh2                 -> echec
  Failed password for invalid user test from 45.156.87.204 port 41740 ssh2   -> echec + invalid user
  Accepted password for adminesisa from 10.10.33.81 port 59176 ssh2         -> reussite
  message repeated 4 times: [ Failed password for root from ...]            -> 4 echecs
"""

logger = get_logger("processing")

# debut commun a toutes les lignes : "May 24 00:28:00 ns sshd[1351222]: "
HEADER = r"(?P<month>\w{3})\s+(?P<day>\d{1,2})\s(?P<time>\d{2}:\d{2}:\d{2})\s\S+\ssshd\[\d+\]:\s"
# ligne regroupee par le systeme : "message repeated 4 times: [ Failed password ..."
REPEAT = r"(?:message repeated (?P<repeat>\d+) times: \[ )?"

FAILED_PATTERN = re.compile(
    HEADER + REPEAT + r"Failed password for (?P<invalid>invalid user )?(?P<user>\S*) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)
ACCEPTED_PATTERN = re.compile(
    HEADER + r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3})"
)


def extract(row: str):
    # row : une ligne de log. Retourne un dictionnaire ou None si la ligne ne nous interesse pas
    if not isinstance(row, str):
        logger.warning(f"Ligne ignoree car ce n'est pas du texte : {row!r}")
        return None

    match = FAILED_PATTERN.search(row)
    if match:
        return {
            "month": match.group("month"),
            "day": int(match.group("day")),
            "time": match.group("time"),
            "user": match.group("user") or "(vide)",  # certains attaquants envoient un user vide
            "ip": match.group("ip"),
            "status": "failed",
            "invalid_user": match.group("invalid") is not None,
            "repeat": int(match.group("repeat") or 1),
        }

    match = ACCEPTED_PATTERN.search(row)
    if match:
        return {
            "month": match.group("month"),
            "day": int(match.group("day")),
            "time": match.group("time"),
            "user": match.group("user"),
            "ip": match.group("ip"),
            "status": "accepted",
            "invalid_user": False,
            "repeat": 1,
        }

    # la ligne contient "password for" mais la regex ne marche pas -> format inattendu
    if "password for" in row:
        logger.warning(f"Format de ligne non reconnu : {row.strip()}")
    return None


def transform(rows: list) -> list:
    events = []
    if not rows:
        logger.warning("Aucune ligne a traiter")
        return events

    for row in rows:
        try:
            event = extract(row)
            if event:
                repeat = event.pop("repeat")
                # une ligne "message repeated 4 times" = 4 tentatives
                for _ in range(repeat):
                    events.append(dict(event))
        except Exception as e:
            logger.exception(f"Erreur pendant l'extraction de la ligne {row!r} : {e}")

    nb_failed = sum(1 for e in events if e["status"] == "failed")
    nb_accepted = len(events) - nb_failed
    logger.info(f"Extraction terminee : {nb_failed} echecs, {nb_accepted} reussites")
    return events


if __name__ == "__main__":
    print(extract("May 24 00:28:00 ns sshd[1351222]: Failed password for invalid user test from 45.156.87.204 port 41740 ssh2"))