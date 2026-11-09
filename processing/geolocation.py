import json
import os
import time

import requests as http

from logger_config import get_logger

"""
Module geolocation : trouve le pays des adresses IP avec l'API ip-api.com
On utilise le mode "batch" : on envoie 100 IP par requete (au lieu d'une requete par IP).
La version gratuite autorise 15 requetes batch par minute -> on attend 4.5 s entre chaque.
Pour ne pas redemander les memes IP, on garde un cache dans geo_cache.json.
"""

logger = get_logger("processing")

CACHE_FILE = "geo_cache.json"
API_URL = "http://ip-api.com/batch?fields=status,message,countryCode,query"
BATCH_SIZE = 100
WAIT_SECONDS = 4.5
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


def geo_batch(ips: list) -> dict:
    # envoie une liste d'IP (max 100) et retourne {ip: code_pays}
    result = {}
    try:
        response = http.post(API_URL, json=ips, timeout=15)
        if response.status_code == 429:
            logger.error("Limite de l'API atteinte (429), attente de 60 s")
            time.sleep(60)
            return result
        if response.status_code != 200:
            logger.error(f"Reponse {response.status_code} de l'API")
            return result
        for item in response.json():
            if item.get("status") == "success" and item.get("countryCode"):
                result[item["query"]] = item["countryCode"]
            else:
                logger.warning(f"Pas de pays pour {item.get('query')} : {item.get('message')}")
    except http.Timeout:
        logger.error("Timeout de l'API")
    except http.ConnectionError:
        logger.error("Pas de connexion internet / API injoignable")
    except ValueError:
        logger.error("Reponse JSON invalide de l'API")
    except http.RequestException as e:
        logger.error(f"Erreur requests : {e}")
    return result


def add_countries(events: list) -> list:
    # ajoute la cle "country" a chaque evenement
    cache = load_cache()

    for e in events:
        if is_private(e["ip"]):
            cache[e["ip"]] = LOCAL

    ips = sorted({e["ip"] for e in events if e["ip"] not in cache})
    logger.info(f"{len(ips)} nouvelles IP a geolocaliser ({len(cache)} deja en cache)")

    errors_in_a_row = 0
    for start in range(0, len(ips), BATCH_SIZE):
        batch = ips[start:start + BATCH_SIZE]
        found = geo_batch(batch)
        if not found:
            errors_in_a_row += 1
            if errors_in_a_row >= 3:
                logger.error("3 erreurs de suite, arret de la geolocalisation")
                break
        else:
            errors_in_a_row = 0
            cache.update(found)
        save_cache(cache)
        logger.info(f"{min(start + BATCH_SIZE, len(ips))}/{len(ips)} IP traitees")
        if start + BATCH_SIZE < len(ips):
            time.sleep(WAIT_SECONDS)  # respecter la limite de 15 requetes par minute

    nb_unknown = sum(1 for e in events if e["ip"] not in cache)
    if nb_unknown:
        logger.warning(f"{nb_unknown} tentatives sans pays (Inconnu)")

    for e in events:
        e["country"] = cache.get(e["ip"], UNKNOWN)
    return events


if __name__ == "__main__":
    print(geo_batch(["88.147.152.239", "8.8.8.8"]))