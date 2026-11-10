import os

import matplotlib.pyplot as plt

from logger_config import get_logger
from storage import database

"""
Module serving : dashboard avec matplotlib.
Les donnees sont lues dans la base PostgreSQL (table auth_events) avec des requetes SQL :
  1. nombre de tentatives echouees par pays
  2. nombre de tentatives reussies par user
  3. tentatives echouees avec invalid user
"""

logger = get_logger("serving")

OUTPUT_DIR = "output"
TOP = 10  # on affiche les 10 plus grandes valeurs pour que le graphique reste lisible


def draw_bar(ax, counts: dict, title: str, xlabel: str, color: str):
    if not counts:
        logger.warning(f"Pas de donnees pour le graphique : {title}")
        ax.text(0.5, 0.5, "Aucune donnee", ha="center", va="center")
        ax.set_title(title)
        return
    ax.bar(list(counts.keys()), list(counts.values()), color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Nombre de tentatives")
    ax.tick_params(axis="x", rotation=45)
    for i, value in enumerate(counts.values()):
        ax.text(i, value, str(value), ha="center", va="bottom", fontsize=8)


def show_dashboard(show: bool = True):
    # lecture des donnees dans la base
    failed_by_country = database.failed_by_country(TOP)
    accepted_by_user = database.accepted_by_user()
    invalid_by_user = database.invalid_user_attempts(TOP)
    nb_invalid = database.count_invalid_user()

    if not failed_by_country and not accepted_by_user and not invalid_by_user:
        logger.error("La base ne renvoie aucune donnee : impossible de construire le dashboard")
        return

    logger.info(f"Donnees lues depuis la base : {len(failed_by_country)} pays, "
                f"{len(accepted_by_user)} users reussis, {nb_invalid} tentatives invalid user")

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Analyse des connexions SSH (auth.log) - source : PostgreSQL")
    draw_bar(axes[0], failed_by_country, f"Tentatives echouees par pays (top {TOP})", "Pays", "tab:red")
    draw_bar(axes[1], accepted_by_user, "Tentatives reussies par user", "User", "tab:green")
    draw_bar(axes[2], invalid_by_user,
             f"Echecs avec invalid user : {nb_invalid} (top {TOP} users)", "User inexistant", "tab:orange")
    fig.tight_layout()

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, "dashboard.png")
        fig.savefig(path)
        logger.info(f"Dashboard enregistre dans {path}")
    except OSError as e:
        logger.error(f"Impossible d'enregistrer le dashboard : {e}")

    if show:
        plt.show()
    plt.close(fig)