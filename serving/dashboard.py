import os

import matplotlib.pyplot as plt

from logger_config import get_logger

"""
Module serving : dashboard avec matplotlib
  1. nombre de tentatives echouees par pays
  2. nombre de tentatives reussies par user
  3. tentatives echouees avec invalid user
"""

logger = get_logger("serving")

OUTPUT_DIR = "output"
TOP = 10  # on affiche les 10 plus grandes valeurs pour que le graphique reste lisible


def count_by(events: list, key: str) -> dict:
    # compte le nombre d'evenements pour chaque valeur de key (ex: chaque pays)
    counts = {}
    for e in events:
        counts[e[key]] = counts.get(e[key], 0) + 1
    # tri du plus grand au plus petit
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def draw_bar(ax, counts: dict, title: str, xlabel: str, color: str):
    top = dict(list(counts.items())[:TOP])
    if not top:
        logger.warning(f"Pas de donnees pour le graphique : {title}")
        ax.text(0.5, 0.5, "Aucune donnee", ha="center", va="center")
        ax.set_title(title)
        return
    ax.bar(list(top.keys()), list(top.values()), color=color)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Nombre de tentatives")
    ax.tick_params(axis="x", rotation=45)
    for i, value in enumerate(top.values()):
        ax.text(i, value, str(value), ha="center", va="bottom", fontsize=8)


def show_dashboard(events: list, show: bool = True):
    if not events:
        logger.error("Aucun evenement : impossible de construire le dashboard")
        return

    failed = [e for e in events if e["status"] == "failed"]
    accepted = [e for e in events if e["status"] == "accepted"]
    invalid = [e for e in failed if e["invalid_user"]]

    failed_by_country = count_by(failed, "country")
    accepted_by_user = count_by(accepted, "user")
    invalid_by_user = count_by(invalid, "user")

    logger.info(f"Echecs : {len(failed)} | Reussites : {len(accepted)} | Invalid user : {len(invalid)}")

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Analyse des connexions SSH (auth.log)")
    draw_bar(axes[0], failed_by_country, f"Tentatives echouees par pays (top {TOP})", "Pays", "tab:red")
    draw_bar(axes[1], accepted_by_user, "Tentatives reussies par user", "User", "tab:green")
    draw_bar(axes[2], invalid_by_user,
             f"Echecs avec invalid user : {len(invalid)} (top {TOP} users)", "User inexistant", "tab:orange")
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