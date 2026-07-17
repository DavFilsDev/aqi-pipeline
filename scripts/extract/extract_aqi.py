import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# Configuration
# ============================================================

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CITIES_FILE = PROJECT_ROOT / "data" / "cities.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


CURRENT_API_URL = (
    "https://api.openweathermap.org/data/2.5/air_pollution"
)

HISTORY_API_URL = (
    "https://api.openweathermap.org/data/2.5/air_pollution/history"
)


AQI_API_KEY = os.getenv("AQI_API_KEY")


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# Charger les villes
# ============================================================

def load_cities() -> list[dict]:
    """
    Charge les villes depuis data/cities.json
    """

    if not CITIES_FILE.exists():
        raise FileNotFoundError(
            f"{CITIES_FILE} introuvable"
        )

    with open(
        CITIES_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# ============================================================
# Appel API OpenWeather
# ============================================================

def fetch_aqi(
    city: dict,
    target_datetime: datetime | None = None
) -> dict:
    """
    Récupère les données AQI d'une ville.

    Si target_datetime est None :
        utilise l'API actuelle.

    Sinon :
        utilise l'API historique.
    """

    if not AQI_API_KEY:
        raise ValueError(
            "AQI_API_KEY absente du .env"
        )


    params = {
        "lat": city["latitude"],
        "lon": city["longitude"],
        "appid": AQI_API_KEY
    }


    # ------------------------------
    # Mode historique
    # ------------------------------

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


    # ------------------------------
    # Mode temps réel
    # ------------------------------

    else:

        url = CURRENT_API_URL



    response = requests.get(
        url,
        params=params,
        timeout=30
    )


    response.raise_for_status()


    return response.json()



# ============================================================
# Construire nom fichier raw
# ============================================================

def build_filename(
    city: dict,
    target_datetime: datetime | None = None
) -> str:
    """
    Exemple :

    paris_2026-07-17T16-00-00.json
    """

    if target_datetime:

        timestamp = target_datetime.strftime(
            "%Y-%m-%dT%H-%M-%S"
        )

    else:

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H-%M-%S"
        )


    city_slug = (
        city["name"]
        .lower()
        .replace(" ", "_")
    )


    return f"{city_slug}_{timestamp}.json"



# ============================================================
# Vérifier existence fichier
# ============================================================

def raw_file_exists(
    city: dict,
    target_datetime: datetime
) -> bool:
    """
    Vérifie si un fichier existe déjà.

    Utilisé pour rendre le backfill rejouable.
    """

    filename = build_filename(
        city,
        target_datetime
    )

    filepath = RAW_DIR / filename

    return filepath.exists()



# ============================================================
# Sauvegarde raw
# ============================================================

def save_raw_json(
    city: dict,
    data: dict,
    target_datetime: datetime | None = None
) -> Path:

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    filename = build_filename(
        city,
        target_datetime
    )


    filepath = RAW_DIR / filename


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
# Fonction principale d'extraction
# ============================================================

def extract_aqi(
    city: dict,
    target_datetime: datetime | None = None
) -> None:
    """
    Extrait les données AQI.

    target_datetime=None :
        collecte actuelle.

    target_datetime fourni :
        collecte historique.
    """

    try:

        # Vérification doublon
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


    except Exception as error:

        logging.error(
            f"Erreur {city['name']} : {error}"
        )



# ============================================================
# Collecte normale
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