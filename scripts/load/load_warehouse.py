"""
Task 4 — Data warehouse loader (Owner: Valisoa)

Reads data/clean/aqi_clean.csv (produced by task 3) and loads it into the
Neon/Postgres star schema defined in sql/schema.sql:

    dim_city  <-\
                 fact_aqi (measures + FKs only)
    dim_time  <-/

Rejouable (safe to re-run):
    - dim_city / dim_time are upserted on their natural keys
      (city+country / timestamp_utc).
    - fact_aqi is upserted on (city_id, time_id): re-running the script
      on the same clean CSV updates the measures in place instead of
      inserting duplicate rows.

Usage:
    python scripts/load/load_warehouse.py
"""

import csv
import logging
import os
import sys
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CLEAN_CSV_PATH = os.path.join("data", "clean", "aqi_clean.csv")

REQUIRED_COLUMNS = [
    "city", "country", "latitude", "longitude",
    "timestamp_utc", "aqi", "pm25", "pm10", "no2", "o3",
]


def get_connection():
    load_dotenv()
    db_url = os.environ.get("NEON_DB_URL")
    if not db_url:
        logger.error("NEON_DB_URL is not set (check your .env file).")
        sys.exit(1)
    return psycopg2.connect(db_url)


def read_clean_csv(path: str):
    if not os.path.exists(path):
        logger.error("Clean CSV not found at %s. Run scripts/transform/build_clean.py first.", path)
        sys.exit(1)

    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            logger.error("Clean CSV is missing required columns: %s", missing)
            sys.exit(1)
        for row in reader:
            rows.append(row)

    if not rows:
        logger.warning("Clean CSV is empty — nothing to load.")
    return rows


def to_float_or_none(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_timestamp(raw_ts: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp, with or without a trailing 'Z'."""
    raw_ts = raw_ts.strip()
    if raw_ts.endswith("Z"):
        raw_ts = raw_ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw_ts)
    return dt.replace(tzinfo=None)


def upsert_dim_city(conn, rows):
    """Upsert every distinct (city, country, lat, lon) and return {(city, country): city_id}."""
    distinct_cities = {}
    for row in rows:
        key = (row["city"], row["country"])
        distinct_cities[key] = (
            row["city"],
            row["country"],
            to_float_or_none(row["latitude"]),
            to_float_or_none(row["longitude"]),
        )

    values = list(distinct_cities.values())
    city_id_by_key = {}

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO dim_city (city, country, latitude, longitude)
            VALUES %s
            ON CONFLICT (city, country)
            DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
            RETURNING city_id, city, country
            """,
            values,
        )
        for city_id, city, country in cur.fetchall():
            city_id_by_key[(city, country)] = city_id

    conn.commit()
    logger.info("dim_city: %d distinct cities upserted.", len(city_id_by_key))
    return city_id_by_key


def upsert_dim_time(conn, rows):
    """Upsert every distinct timestamp and return {timestamp_utc (datetime): time_id}."""
    distinct_ts = {}
    for row in rows:
        dt = parse_timestamp(row["timestamp_utc"])
        if dt not in distinct_ts:
            day_of_week = dt.weekday()
            distinct_ts[dt] = (
                dt,
                dt.date(),
                dt.hour,
                day_of_week,
                day_of_week >= 5,
            )

    values = list(distinct_ts.values())
    time_id_by_ts = {}

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO dim_time (timestamp_utc, date, hour, day_of_week, is_weekend)
            VALUES %s
            ON CONFLICT (timestamp_utc)
            DO UPDATE SET date = EXCLUDED.date,
                          hour = EXCLUDED.hour,
                          day_of_week = EXCLUDED.day_of_week,
                          is_weekend = EXCLUDED.is_weekend
            RETURNING time_id, timestamp_utc
            """,
            values,
        )
        for time_id, timestamp_utc in cur.fetchall():
            time_id_by_ts[timestamp_utc] = time_id

    conn.commit()
    logger.info("dim_time: %d distinct timestamps upserted.", len(time_id_by_ts))
    return time_id_by_ts


def upsert_fact_aqi(conn, rows, city_id_by_key, time_id_by_ts):
    values = []
    for row in rows:
        city_id = city_id_by_key[(row["city"], row["country"])]
        time_id = time_id_by_ts[parse_timestamp(row["timestamp_utc"])]
        values.append((
            city_id,
            time_id,
            to_float_or_none(row["aqi"]),
            to_float_or_none(row["pm25"]),
            to_float_or_none(row["pm10"]),
            to_float_or_none(row["no2"]),
            to_float_or_none(row["o3"]),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO fact_aqi (city_id, time_id, aqi, pm25, pm10, no2, o3)
            VALUES %s
            ON CONFLICT (city_id, time_id)
            DO UPDATE SET aqi = EXCLUDED.aqi,
                          pm25 = EXCLUDED.pm25,
                          pm10 = EXCLUDED.pm10,
                          no2 = EXCLUDED.no2,
                          o3 = EXCLUDED.o3
            """,
            values,
        )
    conn.commit()
    logger.info("fact_aqi: %d rows upserted (no duplicates created on re-run).", len(values))


def main():
    rows = read_clean_csv(CLEAN_CSV_PATH)
    if not rows:
        return

    conn = get_connection()
    try:
        city_id_by_key = upsert_dim_city(conn, rows)
        time_id_by_ts = upsert_dim_time(conn, rows)
        upsert_fact_aqi(conn, rows, city_id_by_key, time_id_by_ts)
    except Exception:
        conn.rollback()
        logger.exception("Load failed, transaction rolled back.")
        sys.exit(1)
    finally:
        conn.close()

    logger.info("Warehouse load complete.")


if __name__ == "__main__":
    main()