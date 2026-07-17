import json
import logging
import os
import time

from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# Configuration
# ============================================================

load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[2]


CITIES_FILE = (
    PROJECT_ROOT
    / "data"
    / "cities.json"
)


RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
)


CURRENT_API_URL = (
    "https://api.openweathermap.org/data/2.5/air_pollution"
)


HISTORY_API_URL = (
    "https://api.openweathermap.org/data/2.5/air_pollution/history"
)


AQI_API_KEY = os.getenv(
    "AQI_API_KEY"
)


REQUEST_TIMEOUT = 30


MAX_RETRY = 3


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
# Charger les villes
# ============================================================

def load_cities() -> list[dict]:
    """
    Charge les villes depuis cities.json
    """

    if not CITIES_FILE.exists():

        raise FileNotFoundError(
            f"Fichier absent : {CITIES_FILE}"
        )


    with open(
        CITIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



# ============================================================
# Appel API AQI
# ============================================================

def fetch_aqi(
    city: dict,
    target_datetime: datetime | None = None
) -> dict:

    """
    Récupère les données pollution.

    - Sans date :
        API temps réel

    - Avec date :
        API historique
    """


    if not AQI_API_KEY:

        raise ValueError(
            "AQI_API_KEY manquante"
        )


    params = {

        "lat": city["latitude"],

        "lon": city["longitude"],

        "appid": AQI_API_KEY

    }


    if target_datetime:


        timestamp = int(
            target_datetime.timestamp()
        )


        params.update(

            {

                "start": timestamp,

                "end": timestamp + 3600

            }

        )


        url = HISTORY_API_URL


    else:

        url = CURRENT_API_URL



    for attempt in range(1, MAX_RETRY + 1):

        try:


            response = requests.get(

                url,

                params=params,

                timeout=REQUEST_TIMEOUT

            )


            response.raise_for_status()


            return response.json()



        except requests.exceptions.RequestException as error:


            logging.warning(

                f"Tentative {attempt}/{MAX_RETRY} "
                f"échouée pour {city['name']} : {error}"

            )


            if attempt < MAX_RETRY:

                time.sleep(
                    attempt * 5
                )

            else:

                raise



# ============================================================
# Nom fichier
# ============================================================

def build_filename(
    city: dict,
    target_datetime: datetime | None = None
):


    if target_datetime:


        date_string = (
            target_datetime
            .strftime(
                "%Y-%m-%dT%H-%M-%S"
            )
        )


    else:


        date_string = (
            datetime.now(
                timezone.utc
            )
            .strftime(
                "%Y-%m-%dT%H-%M-%S"
            )
        )


    city_name = (

        city["name"]
        .lower()
        .replace(
            " ",
            "_"
        )

    )


    return (
        f"{city_name}_{date_string}.json"
    )



# ============================================================
# Vérifier fichier existant
# ============================================================

def raw_file_exists(
    city: dict,
    target_datetime: datetime
):


    filename = build_filename(
        city,
        target_datetime
    )


    filepath = (
        RAW_DIR
        /
        filename
    )


    return filepath.exists()



# ============================================================
# Sauvegarde JSON
# ============================================================

def save_raw_json(
    city: dict,
    data: dict,
    target_datetime: datetime | None = None
):


    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    filename = build_filename(
        city,
        target_datetime
    )


    filepath = (
        RAW_DIR
        /
        filename
    )


    # enrichissement du raw

    data["city"] = city["name"]


    if target_datetime:

        data["timestamp"] = (
            target_datetime
            .astimezone(timezone.utc)
            .isoformat()
        )

    else:

        data["timestamp"] = (
            datetime.now(
                timezone.utc
            )
            .isoformat()
        )



    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:


        json.dump(

            data,

            file,

            indent=2,

            ensure_ascii=False

        )


    return filepath



# ============================================================
# Extraction d'une ville
# ============================================================

def extract_aqi(
    city: dict,
    target_datetime: datetime | None = None
):


    try:


        if target_datetime:


            if raw_file_exists(
                city,
                target_datetime
            ):


                logging.info(

                    f"Skip {city['name']} "
                    f"{target_datetime}"

                )

                return



        logging.info(

            f"Extraction : {city['name']}"

        )


        data = fetch_aqi(

            city,

            target_datetime

        )


        filepath = save_raw_json(

            city,

            data,

            target_datetime

        )


        logging.info(

            f"Sauvegardé : {filepath}"

        )



    except KeyboardInterrupt:


        logging.warning(

            "Extraction interrompue par utilisateur"

        )

        raise



    except Exception as error:


        logging.error(

            f"Erreur {city['name']} : {error}"

        )



# ============================================================
# Mode temps réel
# ============================================================

def main():


    cities = load_cities()


    logging.info(

        f"{len(cities)} villes chargées"

    )


    for city in cities:


        extract_aqi(city)



if __name__ == "__main__":

    main()