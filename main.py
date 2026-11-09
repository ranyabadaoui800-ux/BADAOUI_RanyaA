import sys

from logger_config import get_logger
from ingestion import read
from processing import extract_transform, geolocation
from storage import save
from serving import dashboard

"""
Pipeline : ingestion -> processing (extraction + geolocalisation) -> storage -> serving (dashboard)
"""

logger = get_logger("main")


def run():
    logger.info("Demarrage du pipeline")

    rows = read.ingest("./data")
    if not rows:
        logger.error("Aucune ligne lue, arret du pipeline")
        return

    events = extract_transform.transform(rows)
    if not events:
        logger.error("Aucun evenement extrait, arret du pipeline")
        return

    events = geolocation.add_countries(events)
    save.save_events(events)

    # "--no-show" : genere l'image sans ouvrir la fenetre
    dashboard.show_dashboard(events, show="--no-show" not in sys.argv)
    logger.info("Pipeline termine")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.warning("Pipeline interrompu par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur non geree : {e}", exc_info=True)