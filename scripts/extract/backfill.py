from datetime import datetime, timedelta, timezone
import logging

from scripts.extract.extract_aqi import (
    load_cities,
    extract_aqi
)


# ============================================================
# Configuration
# ============================================================

# Nombre de mois à récupérer
BACKFILL_MONTHS = 3


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "- %(levelname)s "
        "- %(message)s"
    )
)


# ============================================================
# Calcul période
# ============================================================

def get_start_date(months: int) -> datetime:
    """
    Retourne la date de début du backfill.
    """

    now = datetime.now(timezone.utc)

    if months == 0:

        return now - timedelta(hours=2)


    return now - timedelta(
        days=months * 30
    )



def get_end_date() -> datetime:
    """
    Retourne la date de fin du backfill.
    """

    return datetime.now(timezone.utc)



# ============================================================
# Normalisation date
# ============================================================

def normalize_hour(date: datetime) -> datetime:
    """
    Transforme une date en heure pile.
    Exemple:
    17:20:35 -> 17:00:00
    """

    return date.replace(
        minute=0,
        second=0,
        microsecond=0
    )



# ============================================================
# Exécution backfill
# ============================================================

def run_backfill():

    cities = load_cities()


    start_date = normalize_hour(
        get_start_date(
            BACKFILL_MONTHS
        )
    )


    end_date = normalize_hour(
        get_end_date()
    )


    logging.info(
        f"Backfill de {start_date} "
        f"à {end_date}"
    )


    current_date = start_date


    total_hours = int(
        (
            end_date - start_date
        ).total_seconds()
        // 3600
    )


    logging.info(
        f"Nombre d'heures à traiter : {total_hours}"
    )



    while current_date <= end_date:


        logging.info(
            f"Traitement date : {current_date}"
        )


        for city in cities:


            extract_aqi(
                city,
                current_date
            )



        current_date += timedelta(
            hours=1
        )



    logging.info(
        "Backfill terminé avec succès"
    )



# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    run_backfill()