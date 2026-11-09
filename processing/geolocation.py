import json
import os

import requests as http

from logger_config import get_logger

"""
Module geolocation : trouve le pays d'une adresse IP avec l'API ipinfo.io
Pour ne pas appeler l'API plusieurs fois pour la meme IP, on garde un cache
dans un fichier json (geo_cache.json).
"""

logger = get_logger("processing")

CACHE_FILE = "geo_cache.json"
API_URL = "https://ipinfo.io/{}/json"
UNKNOWN = "Inconnu"
LOCAL = "Local"


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"{CACHE_FILE} est corrompu, on repart d'un cache vide")
    except OSError as e:
        logger.error(f"Impossible de lire {CACHE_FILE} : {e}")
    return {}


def save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError as e:
        logger.error(f"Impossible d'enregistrer {CACHE_FILE} : {e}")


def is_private(ip: str) -> bool:
    # IP locales / privees : elles n'ont pas de pays
    if ip.startswith(("10.", "127.", "192.168.")):
        return True
    if ip.startswith("172."):
        second = int(ip.split(".")[1])
        return 16 <= second <= 31
    return False


def geo_location(ip: str) -> str:
    # retourne le code pays (ex: "FR", "CN") ou "Local" / "Inconnu"
    if is_private(ip):
        logger.debug(f"{ip} est une IP privee")
        return LOCAL
    try:
        response = http.get(API_URL.format(ip), timeout=5)
        if response.status_code == 429:
            logger.error("Limite de l'API ipinfo atteinte (429)")
            return UNKNOWN
        if response.status_code != 200:
            logger.error(f"Reponse {response.status_code} de l'API pour {ip}")
            return UNKNOWN
        country = response.json().get("country")
        if not country:
            logger.warning(f"Pas de pays dans la reponse pour {ip}")
            return UNKNOWN
        return country
    except http.Timeout:
        logger.error(f"Timeout de l'API pour {ip}")
    except http.ConnectionError:
        logger.error(f"Pas de connexion internet / API injoignable pour {ip}")
    except ValueError:
        logger.error(f"Reponse JSON invalide pour {ip}")
    except http.RequestException as e:
        logger.error(f"Erreur requests pour {ip} : {e}")
    return UNKNOWN


def add_countries(events: list) -> list:
    # ajoute la cle "country" a chaque evenement
    cache = load_cache()
    ips = {e["ip"] for e in events if e["ip"] not in cache}
    logger.info(f"{len(ips)} nouvelles IP a geolocaliser ({len(cache)} deja en cache)")

    errors_in_a_row = 0
    for i, ip in enumerate(ips, start=1):
        country = geo_location(ip)
        if country == UNKNOWN:
            errors_in_a_row += 1
            if errors_in_a_row >= 5:
                # 5 echecs de suite : l'API est surement inaccessible, on arrete
                logger.error("5 erreurs de suite, arret de la geolocalisation")
                break
        else:
            errors_in_a_row = 0
            cache[ip] = country  # on ne met en cache que les vraies reponses
        if i % 100 == 0:
            logger.info(f"{i}/{len(ips)} IP geolocalisees")
            save_cache(cache)
    save_cache(cache)

    for e in events:
        e["country"] = cache.get(e["ip"], UNKNOWN)
    return events


if __name__ == "__main__":
    print(geo_location("88.147.152.239"))