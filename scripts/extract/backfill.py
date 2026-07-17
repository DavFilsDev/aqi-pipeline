from datetime import datetime, timedelta, timezone

from scripts.extract.extract_aqi import (
    load_cities,
    extract_aqi
)


# ============================================================
# Configuration
# ============================================================

# Test : 2 dernières heures
# Production :
# BACKFILL_MONTHS = 3 ou 12
BACKFILL_MONTHS = 0


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

    return now - timedelta(days=months * 30)


def get_end_date() -> datetime:
    """
    Retourne la date de fin du backfill.
    """

    return datetime.now(timezone.utc)



# ============================================================
# Exécution du backfill
# ============================================================

def run_backfill():

    cities = load_cities()

    start_date = get_start_date(
        BACKFILL_MONTHS
    )

    end_date = get_end_date()


    print(
        f"Backfill de {start_date} à {end_date}"
    )


    current_date = start_date


    while current_date <= end_date:

        current_date = current_date.replace(
            minute=0,
            second=0,
            microsecond=0
        )


        print(
            f"\nDate : {current_date}"
        )


        for city in cities:

            extract_aqi(
                city,
                current_date
            )


        current_date += timedelta(hours=1)



# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    run_backfill()