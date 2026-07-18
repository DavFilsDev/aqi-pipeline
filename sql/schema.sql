-- ============================================================
-- AQI Pipeline — Data Warehouse Schema (star schema)
-- Owner: Valisoa (Task 4)
--
-- Design:
--   fact_aqi   -> measures only (aqi, pm25, pm10, no2, o3) + FKs
--   dim_city   -> descriptive city attributes, no measures
--   dim_time   -> descriptive time attributes, no measures
--
-- Idempotency:
--   - dim_city  : UNIQUE (city, country)          -> upsert-safe
--   - dim_time  : UNIQUE (timestamp_utc)           -> upsert-safe
--   - fact_aqi  : UNIQUE (city_id, time_id)        -> re-running the
--     loader can never create a duplicate fact row for the same
--     city + hour; it will just update the measures (see
--     load_warehouse.py, ON CONFLICT ... DO UPDATE).
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_city (
    city_id     SERIAL PRIMARY KEY,
    city        TEXT NOT NULL,
    country     TEXT NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_dim_city UNIQUE (city, country)
);

CREATE TABLE IF NOT EXISTS dim_time (
    time_id         SERIAL PRIMARY KEY,
    timestamp_utc   TIMESTAMP NOT NULL,
    date            DATE NOT NULL,
    hour            SMALLINT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_of_week     SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0 = Monday .. 6 = Sunday
    is_weekend      BOOLEAN NOT NULL,
    CONSTRAINT uq_dim_time UNIQUE (timestamp_utc)
);

CREATE TABLE IF NOT EXISTS fact_aqi (
    fact_id     BIGSERIAL PRIMARY KEY,
    city_id     INTEGER NOT NULL REFERENCES dim_city (city_id),
    time_id     INTEGER NOT NULL REFERENCES dim_time (time_id),
    aqi         DOUBLE PRECISION,
    pm25        DOUBLE PRECISION,
    pm10        DOUBLE PRECISION,
    no2         DOUBLE PRECISION,
    o3          DOUBLE PRECISION,
    CONSTRAINT uq_fact_aqi UNIQUE (city_id, time_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_aqi_city ON fact_aqi (city_id);
CREATE INDEX IF NOT EXISTS idx_fact_aqi_time ON fact_aqi (time_id);
CREATE INDEX IF NOT EXISTS idx_dim_time_date ON dim_time (date);