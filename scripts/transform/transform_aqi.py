import json
import csv
import logging
from pathlib import Path
from datetime import datetime

 
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"

OUTPUT_FILE = CLEAN_DIR / "aqi_clean.csv"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
 

CSV_COLUMNS = [
    "city",
    "country",
    "latitude",
    "longitude",
    "timestamp",
    "aqi",
    "pm2_5",
    "pm10",
    "co",
    "no",
    "no2",
    "o3",
    "so2"
]

 

def load_raw_files():

    files = list(RAW_DIR.glob("*.json"))

    logging.info(
        f"{len(files)} fichiers raw trouvés"
    )

    return files


 

def transform_file(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    city = data["city"]

    country = data["country"]

    latitude = data["latitude"]

    longitude = data["longitude"]


    timestamp = data["timestamp"]


    components = data["components"]


    row = {

        "city": city,

        "country": country,

        "latitude": latitude,

        "longitude": longitude,

        "timestamp": timestamp,


        "aqi": data["aqi"],


        "pm2_5": components.get(
            "pm2_5"
        ),

        "pm10": components.get(
            "pm10"
        ),

        "co": components.get(
            "co"
        ),

        "no": components.get(
            "no"
        ),

        "no2": components.get(
            "no2"
        ),

        "o3": components.get(
            "o3"
        ),

        "so2": components.get(
            "so2"
        )
    }


    return row


 

def build_clean():

    rows = []


    files = load_raw_files()


    for file in files:

        try:

            row = transform_file(file)

            rows.append(row)


        except Exception as error:

            logging.error(
                f"Erreur {file}: {error}"
            )



    logging.info(
        f"{len(rows)} lignes générées"
    )


    unique_rows = {

        (
            row["city"],
            row["timestamp"]

        ): row

        for row in rows
    }


    rows = list(
        unique_rows.values()
    )


 
    rows.sort(
        key=lambda x:
        datetime.fromisoformat(
            x["timestamp"]
            .replace(
                "Z",
                "+00:00"
            )
        )
    )


    CLEAN_DIR.mkdir(
        exist_ok=True
    )


    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:


        writer = csv.DictWriter(
            file,
            fieldnames=CSV_COLUMNS
        )


        writer.writeheader()


        writer.writerows(
            rows
        )


    logging.info(
        f"Clean créé : {OUTPUT_FILE}"
    )


    logging.info(
        f"{len(rows)} lignes finales"
    )


 

if __name__ == "__main__":

    build_clean()