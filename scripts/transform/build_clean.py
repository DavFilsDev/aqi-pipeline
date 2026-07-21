import json
import pandas as pd
from pathlib import Path

# Chemins du projet

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_FOLDER = BASE_DIR / "data" / "raw"
OUTPUT_FILE = BASE_DIR / "data" / "clean" / "aqi_clean.csv"


# Extraction d'une ligne depuis un JSON

def extract_row(data):

    city = data.get("city") or data.get("name")

    country = data.get("country")

    latitude = data.get("latitude") or data.get("lat")

    longitude = data.get("longitude") or data.get("lon")

    aqi = data.get("aqi") or data.get("AQI")

    pm25 = data.get("pm25")

    pm10 = data.get("pm10")

    no2 = data.get("no2")

    o3 = data.get("o3")

    timestamp = (
        data.get("timestamp_utc")
        or data.get("timestamp")
        or data.get("time")
    )

    return {
        "city": city,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp_utc": timestamp,
        "aqi": aqi,
        "pm25": pm25,
        "pm10": pm10,
        "no2": no2,
        "o3": o3
    }

# Lecture des fichiers RAW

def read_raw_files():

    rows = []

    files = list(RAW_FOLDER.glob("*.json"))

    print(f"{len(files)} fichiers JSON trouvés")

    for file in files:

        try:

            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            row = extract_row(data)

            row["raw_file_time"] = file.stat().st_mtime

            rows.append(row)

        except Exception as e:

            print(f"Erreur avec {file.name} : {e}")

    return rows


# Transformation RAW -> CLEAN

def build_clean():

    rows = read_raw_files()

    if not rows:
        print("Aucune donnée trouvée dans data/raw")
        return

    df = pd.DataFrame(rows)

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["city", "timestamp_utc"]
    )

    df["hour"] = df["timestamp_utc"].dt.floor("h")

    df = df.sort_values(
        by=["city", "hour", "raw_file_time"]
    )

    df = df.drop_duplicates(
        subset=["city", "hour"],
        keep="last"
    )

    df = df.sort_values(
        by=["timestamp_utc", "city"]
    )

    df = df[
        [
            "city",
            "country",
            "latitude",
            "longitude",
            "timestamp_utc",
            "aqi",
            "pm25",
            "pm10",
            "no2",
            "o3",
        ]
    ]
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )
    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nTransformation terminée")
    print(f"Fichier créé : {OUTPUT_FILE}")
    print(f"Nombre de lignes : {len(df)}")
    print(df)


# Programme principal

if __name__ == "__main__":
    build_clean()