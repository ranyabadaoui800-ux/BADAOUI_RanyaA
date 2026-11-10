import os

import psycopg2
from psycopg2.extras import execute_values

from logger_config import get_logger

"""
Module storage : enregistre les tentatives de connexion dans PostgreSQL
et fournit les requetes SQL utilisees par le dashboard.

Avant de lancer : PostgreSQL doit etre demarre. Le mot de passe est lu dans
la variable d'environnement DB_PASSWORD (pour ne pas le mettre sur GitHub).
Dans PowerShell :  $env:DB_PASSWORD="ton_mot_de_passe"
"""

logger = get_logger("storage")

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "postgres"),
    "dbname": os.environ.get("DB_NAME", "log_analysis"),
}

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS auth_events (
    id SERIAL PRIMARY KEY,
    month VARCHAR(3),
    day INTEGER,
    time VARCHAR(8),
    username VARCHAR(100),
    ip VARCHAR(15),
    country VARCHAR(20),
    status VARCHAR(10),
    invalid_user BOOLEAN
)
"""


def create_database():
    # cree la base log_analysis si elle n'existe pas (connexion a la base par defaut "postgres")
    config = dict(DB_CONFIG, dbname="postgres")
    conn = None
    try:
        conn = psycopg2.connect(**config)
        conn.autocommit = True  # CREATE DATABASE ne peut pas etre dans une transaction
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG["dbname"],))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{DB_CONFIG["dbname"]}"')
                logger.info(f"Base {DB_CONFIG['dbname']} creee")
        return True
    except psycopg2.OperationalError as e:
        logger.error(f"Connexion a PostgreSQL impossible (serveur demarre ? mot de passe ?) : {e}")
    except psycopg2.Error as e:
        logger.error(f"Erreur lors de la creation de la base : {e}")
    finally:
        if conn:
            conn.close()
    return False


def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        logger.error(f"Connexion a la base {DB_CONFIG['dbname']} impossible : {e}")
        return None


def save_events(events: list) -> bool:
    if not events:
        logger.warning("Aucun evenement a enregistrer dans la base")
        return False
    if not create_database():
        return False
    conn = get_connection()
    if conn is None:
        return False

    rows = [
        (e["month"], e["day"], e["time"], e["user"], e["ip"], e["country"], e["status"], e["invalid_user"])
        for e in events
    ]
    try:
        with conn:  # commit automatique si tout va bien, rollback si erreur
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE)
                cur.execute("TRUNCATE auth_events RESTART IDENTITY")  # on vide pour ne pas avoir de doublons
                execute_values(
                    cur,
                    "INSERT INTO auth_events (month, day, time, username, ip, country, status, invalid_user) VALUES %s",
                    rows,
                )
        logger.info(f"{len(rows)} evenements enregistres dans la table auth_events")
        return True
    except KeyError as e:
        logger.error(f"Champ manquant dans un evenement : {e}")
    except psycopg2.Error as e:
        logger.error(f"Erreur SQL pendant l'insertion : {e}")
    finally:
        conn.close()
    return False


def query(sql: str) -> dict:
    # execute une requete SQL qui retourne 2 colonnes (label, nombre) -> {label: nombre}
    conn = get_connection()
    if conn is None:
        return {}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return {label: count for label, count in cur.fetchall()}
    except psycopg2.Error as e:
        logger.error(f"Erreur SQL : {e}")
        return {}
    finally:
        conn.close()


def failed_by_country(limit: int = 10) -> dict:
    return query(f"""
        SELECT country, COUNT(*) AS total
        FROM auth_events
        WHERE status = 'failed'
        GROUP BY country
        ORDER BY total DESC
        LIMIT {int(limit)}
    """)


def accepted_by_user() -> dict:
    return query("""
        SELECT username, COUNT(*) AS total
        FROM auth_events
        WHERE status = 'accepted'
        GROUP BY username
        ORDER BY total DESC
    """)


def invalid_user_attempts(limit: int = 10) -> dict:
    return query(f"""
        SELECT username, COUNT(*) AS total
        FROM auth_events
        WHERE status = 'failed' AND invalid_user = TRUE
        GROUP BY username
        ORDER BY total DESC
        LIMIT {int(limit)}
    """)


def count_invalid_user() -> int:
    result = query("SELECT 'total', COUNT(*) FROM auth_events WHERE status = 'failed' AND invalid_user = TRUE")
    return result.get("total", 0)