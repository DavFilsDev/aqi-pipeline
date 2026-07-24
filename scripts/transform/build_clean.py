import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_FOLDER = BASE_DIR / "data" / "raw"
OUTPUT_FILE = BASE_DIR / "data" / "clean" / "aqi_clean.csv"


def extract_row(data):
    entry = (data.get("list") or [{}])[0]
    main = entry.get("main", {})
    components = entry.get("components", {})
    coords = data.get("coordinates", {})

    return {
        "city": data.get("city"),
        "country": data.get("country"),
        "latitude": coords.get("latitude"),
        "longitude": coords.get("longitude"),
        "timestamp_utc": data.get("timestamp"),
        "aqi": main.get("aqi"),
        "pm25": components.get("pm2_5"),
        "pm10": components.get("pm10"),
        "no2": components.get("no2"),
        "o3": components.get("o3"),
    }


def read_raw_files():
    rows = []
    files = list(RAW_FOLDER.glob("*.json"))
    print(f"{len(files)} raw JSON files found")

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            row = extract_row(data)
            row["raw_file_time"] = file.stat().st_mtime
            rows.append(row)
        except Exception as e:
            print(f"Error reading {file.name}: {e}")

    return rows


def build_clean():
    rows = read_raw_files()

    if not rows:
        print("No data found in data/raw — nothing to build.")
        return

    df = pd.DataFrame(rows)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    df = df.dropna(subset=["city", "timestamp_utc"])

    df["hour"] = df["timestamp_utc"].dt.floor("h")
    df = df.sort_values(by=["city", "hour", "raw_file_time"])
    df = df.drop_duplicates(subset=["city", "hour"], keep="last")
    df = df.sort_values(by=["timestamp_utc", "city"])

    df = df[[
        "city", "country", "latitude", "longitude",
        "timestamp_utc", "aqi", "pm25", "pm10", "no2", "o3",
    ]]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nBuilt {OUTPUT_FILE} — {len(df)} rows, {df['city'].nunique()} cities")


if __name__ == "__main__":
    build_clean()