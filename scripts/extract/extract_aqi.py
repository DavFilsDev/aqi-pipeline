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

API_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

AQI_API_KEY = os.getenv("AQI_API_KEY")


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# Lecture des villes
# ============================================================

def load_cities() -> list[dict]:
    """
    Charge les villes depuis data/cities.json
    """

    if not CITIES_FILE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {CITIES_FILE}"
        )

    with open(CITIES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# Appel API OpenWeather
# ============================================================

def fetch_aqi(city: dict) -> dict:
    """
    Appelle OpenWeather Air Pollution API
    pour une ville donnée.

    Retourne la réponse JSON brute.
    """

    if not AQI_API_KEY:
        raise ValueError(
            "AQI_API_KEY absente dans le fichier .env"
        )

    params = {
        "lat": city["latitude"],
        "lon": city["longitude"],
        "appid": AQI_API_KEY
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# Nom du fichier raw
# ============================================================

def build_filename(city: dict) -> str:
    """
    Construit le nom du fichier raw.

    Exemple :
    paris_2026-07-17T15-30-00.json
    """

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
# Sauvegarde JSON brut
# ============================================================

def save_raw_json(
    city: dict,
    data: dict
) -> Path:
    """
    Sauvegarde la réponse API sans modification
    dans data/raw/
    """

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = build_filename(city)

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
# Fonction principale demandée par le sujet
# ============================================================

def extract_aqi(city: dict) -> None:
    """
    Extrait les données AQI d'une ville
    et sauvegarde le JSON brut.

    Une erreur sur une ville ne doit pas
    arrêter tout le pipeline.
    """

    try:

        logging.info(
            f"Extraction AQI : {city['name']}"
        )

        data = fetch_aqi(city)

        filepath = save_raw_json(
            city,
            data
        )

        logging.info(
            f"Fichier créé : {filepath}"
        )


    except Exception as error:

        logging.error(
            f"Erreur pour {city['name']} : {error}"
        )


# ============================================================
# Point d'entrée
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