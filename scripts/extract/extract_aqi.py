import json
import logging
import os
import time

from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

 

if load_dotenv:
    load_dotenv()
else:
    logging.warning(
        "python-dotenv is not installed. "
        "Environment variables must already be configured."
    )


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

 

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "- %(levelname)s "
        "- %(message)s"
    ),
    handlers=[
        logging.FileHandler("extraction.log"),
        logging.StreamHandler()
    ]
)
 

def load_cities() -> list[dict]:
    """
    Load cities configuration from cities.json.
    """

    try:

        if not CITIES_FILE.exists():

            raise FileNotFoundError(
                f"Cities file not found: {CITIES_FILE}"
            )


        with open(
            CITIES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            cities = json.load(file)


        if not isinstance(cities, list):

            raise ValueError(
                "cities.json must contain a list"
            )


        return cities


    except json.JSONDecodeError as error:

        logging.error(
            f"Invalid JSON format in cities file: {error}"
        )

        raise


    except Exception as error:

        logging.error(
            f"Failed to load cities: {error}"
        )

        raise
 

def fetch_aqi(
    city: dict,
    target_datetime: datetime | None = None
) -> dict:

    """
    Fetch air quality data from OpenWeather API.

    If target_datetime is None:
        Uses current AQI endpoint.

    If target_datetime is provided:
        Uses historical AQI endpoint.
    """


    try:


        if not AQI_API_KEY:

            raise ValueError(
                "AQI_API_KEY is missing"
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



        for attempt in range(
            1,
            MAX_RETRY + 1
        ):

            try:


                response = requests.get(

                    url,

                    params=params,

                    timeout=REQUEST_TIMEOUT

                )


                response.raise_for_status()


                try:

                    return response.json()


                except ValueError as error:

                    logging.error(

                        f"Invalid JSON response "
                        f"for {city['name']}: {error}"

                    )

                    raise



            except requests.exceptions.RequestException as error:


                logging.warning(

                    f"Attempt {attempt}/{MAX_RETRY} "
                    f"failed for {city['name']}: {error}"

                )


                if attempt < MAX_RETRY:

                    time.sleep(
                        attempt * 5
                    )

                else:

                    raise



    except Exception as error:

        logging.error(

            f"Failed to fetch AQI for "
            f"{city.get('name', 'unknown')}: {error}"

        )

        raise

 

def build_filename(
    city: dict,
    target_datetime: datetime | None = None
) -> str:

    """
    Build raw JSON filename.
    """


    try:


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


    except Exception as error:

        logging.error(
            f"Filename creation failed: {error}"
        )

        raise
 

def raw_file_exists(
    city: dict,
    target_datetime: datetime
) -> bool:

    """
    Check if raw file already exists.
    """


    try:

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


    except Exception as error:

        logging.error(
            f"Failed checking existing file: {error}"
        )

        raise

 

def save_raw_json(
    city: dict,
    data: dict,
    target_datetime: datetime | None = None
):

    """
    Save AQI data enriched with city information.
    """


    try:


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


 
        data["city"] = city["name"]


        data["country"] = city.get(
            "country",
            "Unknown"
        )


        data["coordinates"] = {

            "latitude": city["latitude"],

            "longitude": city["longitude"]

        }


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



    except KeyError as error:

        logging.error(
            f"Missing city information: {error}"
        )

        raise


    except IOError as error:

        logging.error(
            f"File writing error: {error}"
        )

        raise


    except Exception as error:

        logging.error(
            f"Failed saving raw data: {error}"
        )

        raise


 

def extract_aqi(
    city: dict,
    target_datetime: datetime | None = None
):

    """
    Extract and save AQI data for one city.
    """


    try:


        if target_datetime:


            if raw_file_exists(
                city,
                target_datetime
            ):


                logging.info(

                    f"Skipping existing file "
                    f"{city['name']} {target_datetime}"

                )

                return



        logging.info(

            f"Extracting : {city['name']}"

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

            f"Saved : {filepath}"

        )



    except KeyboardInterrupt:

        logging.warning(
            "Extraction interrupted by user"
        )

        raise



    except Exception as error:

        logging.error(

            f"Extraction failed for "
            f"{city.get('name', 'unknown')}: {error}"

        )
 
def main():

    """
    Extract current AQI for all cities.
    """


    try:


        cities = load_cities()


        logging.info(

            f"{len(cities)} cities loaded"

        )


        for city in cities:

            extract_aqi(city)



    except KeyboardInterrupt:


        logging.warning(
            "Program interrupted by user"
        )



    except Exception as error:


        logging.error(

            f"Application error: {error}"

        )

        raise

 

if __name__ == "__main__":

    main()