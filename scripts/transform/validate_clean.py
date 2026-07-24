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
    "city", "country", "latitude", "longitude", "timestamp_utc", "aqi",
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

    duplicates = df.duplicated(
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

    cities = df["city"].unique()

    logging.info(
        f"{len(cities)} cities detected"
    )

    print(
        cities
    )

    logging.info(
        "Validation completed successfully"
    )

if __name__ == "__main__":
    validate()