import pandas as pd
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parents[2]

CLEAN_FILE = (
    BASE_DIR /
    "data" /
    "clean" /
    "aqi_clean.csv"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)

REQUIRED_COLUMNS = [
    "city", "country", "latitude", "longitude", "timestamp_utc",
    "aqi", "pm25", "pm10", "no2", "o3",
]

def validate():
    if not CLEAN_FILE.exists():
        raise Exception(
            "The clean file does not exist"
        )
    df = pd.read_csv(
        CLEAN_FILE
    )
    logging.info(
        f"{len(df)} rows found"
    )
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            raise Exception(
                f"Missing column: {column}"
            )

    logging.info(
        "Columns validated successfully"
    )

    null_counts = df[REQUIRED_COLUMNS].isnull().sum()
    columns_with_nulls = null_counts[null_counts > 0]

    if not columns_with_nulls.empty:
        details = ", ".join(
            f"{col}={count}" for col, count in columns_with_nulls.items()
        )
        raise Exception(
            f"Null values found in required columns: {details}"
        )

    logging.info(
        "No null values in required columns"
    )

    duplicates =  df.duplicated(
        subset=[
            "city",
            "timestamp_utc"
        ]
    ).sum()

    if duplicates > 0:
        raise Exception(
            f"{duplicates} duplicates found"
        )

    logging.info(
        "No duplicates found"
    )

    timestamps = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True, format="mixed")

    if timestamps.isnull().any():
        raise Exception(
            f"{timestamps.isnull().sum()} timestamp_utc values could not be parsed"
        )

    off_the_hour = ((timestamps.dt.minute != 0) | (timestamps.dt.second != 0)).sum()
    if off_the_hour > 0:
        raise Exception(
            f"{off_the_hour} rows have a timestamp_utc not floored to the hour "
            "(one row per city+hour is required)"
        )

    logging.info(
        "All timestamps are valid and floored to the hour"
    )

    sort_key = pd.DataFrame({"timestamp_utc": timestamps, "city": df["city"]})
    expected_order = sort_key.sort_values(by=["timestamp_utc", "city"]).index

    if not (expected_order == sort_key.index).all():
        raise Exception(
            "Rows are not sorted chronologically (by timestamp_utc, then city)"
        )

    logging.info(
        "Rows are in chronological order"
    )

    cities = df["city"].unique()

    logging.info(
        f"{len(cities)} cities detected"
    )

    print(
        cities
    )

    logging.info(
        f"Period covered: {timestamps.min()} -> {timestamps.max()}"
    )

    logging.info(
        "Validation completed successfully"
    )

if __name__ == "__main__":
    validate()