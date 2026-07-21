from datetime import datetime, timedelta, timezone
import logging

from scripts.extract.extract_aqi import (
    load_cities,
    extract_aqi
)

BACKFILL_MONTHS = 3

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "- %(levelname)s "
        "- %(message)s"
    )
)


def get_start_date(months: int) -> datetime:
    """
    Returns the start date for the backfill.
    """

    now = datetime.now(timezone.utc)

    if months == 0:
        return now - timedelta(hours=2)

    return now - timedelta(
        days=months * 30
    )


def get_end_date() -> datetime:
    """
    Returns the end date for the backfill.
    """

    return datetime.now(timezone.utc)


def normalize_hour(date: datetime) -> datetime:
    """
    Rounds a datetime down to the beginning of the hour.

    Example:
    17:20:35 -> 17:00:00
    """

    return date.replace(
        minute=0,
        second=0,
        microsecond=0
    )


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
        f"Backfill from {start_date} "
        f"to {end_date}"
    )

    current_date = start_date

    total_hours = int(
        (
            end_date - start_date
        ).total_seconds()
     )

    logging.info(
        f"Total hours to process: {total_hours}"
    )

    while current_date <= end_date:

        logging.info(
            f"Processing date: {current_date}"
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
        "Backfill completed successfully"
    )


if __name__ == "__main__":

    run_backfill()