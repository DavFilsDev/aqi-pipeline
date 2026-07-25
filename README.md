# AQI Pipeline

Automated pipeline collecting Air Quality Index (AQI) data for 5 cities, every hour,
24/7. Orchestrated with GitHub Actions, stored as versioned raw/clean files in this
repository, and loaded into a dimensional data warehouse hosted on Neon (Postgres).

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the stack and justification, and
[TASK.md](./TASK.md) for the team's task breakdown.

## Cities covered

| City | Country | Latitude | Longitude |
|---|---|---|---|
| Paris | France | 48.8566 | 2.3522 |
| Madrid | Spain | 40.4168 | -3.7038 |
| Buenos Aires | Argentina | -34.6037 | -58.3816 |
| London | England | 51.5074 | -0.1278 |
| Antananarivo | Madagascar | -18.8792 | 47.5079 |

## Data contract — `data/clean/aqi_clean.csv`

One row per city per hour, sorted chronologically, no duplicates
(deduplication key: city + hour).

| Column | Type | Unit / notes |
|---|---|---|
| `city` | string | city name, matches the table above |
| `country` | string | country name |
| `latitude` | float | decimal degrees |
| `longitude` | float | decimal degrees |
| `timestamp_utc` | ISO-8601 datetime | UTC, floored to the hour |
| `aqi` | integer | OpenWeather AQI index, 1 (Good) to 5 (Very Poor) |
| `pm25` | float | µg/m³ — fine particulate matter (PM2.5) |
| `pm10` | float | µg/m³ — coarse particulate matter (PM10) |
| `no2` | float | µg/m³ — nitrogen dioxide |
| `o3` | float | µg/m³ — ozone |

Source: [OpenWeather Air Pollution API](https://openweathermap.org/api/air-pollution).

## Warehouse schema (star schema)

- **`fact_aqi`** — one row per (city, hour): `aqi`, `pm25`, `pm10`, `no2`, `o3`,
  `city_id` (FK), `time_id` (FK). No descriptive columns.
- **`dim_city`** — `city_id`, `name`, `country`, `latitude`, `longitude`. No measures.
- **`dim_time`** — `time_id`, `date`, `hour`, `day_of_week`, `is_weekend`. No measures.

Star schema chosen (no snowflaking): the two dimensions are small and flat, no
benefit from further normalization.

## Period covered & known gaps

<!-- TO FILL once your backfill on main completes — example: -->
- Backfill: <start-date> to <end-date> (hourly), for all 5 cities.
- Continuous hourly collection since <first successful pipeline.yml run date>.
- Known gaps: <list any, e.g. "OpenWeather's history endpoint only returns data
  from <date> onward for some cities" or "N hours missing on <date> due to a
  transient API error — see run <link> in the Actions history">.

Expected row count in `fact_aqi` ≈ 5 cities × hours covered. Any discrepancy is
explained above.

## Database connection (read-only, for grading)

- Host: `<neon-host>`
- Database: `<db-name>`
- Read-only role: `<readonly-username>` — request password from the team, or use:
  `postgresql://<readonly-user>:<password>@<host>/<db>?sslmode=require`

(The pipeline itself uses a separate, write-capable connection string, stored
only in GitHub Actions secrets — never in this repo.)

## Local setup (Windows / macOS / Linux)

### 1. Clone and configure
```bash
git clone https://github.com/DavFilsDev/aqi-pipeline.git
cd aqi-pipeline
cp .env.example .env
```
Fill in `.env` with your own AQI API key and the Neon connection string.

### 2. Install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 3. Run the pipeline manually, step by step
```bash
python scripts/extract/extract_aqi.py
python scripts/transform/build_clean.py
python scripts/transform/validate_clean.py
python scripts/load/load_warehouse.py
```

### 4. Automated runs
The pipeline runs automatically every hour via GitHub Actions
(`.github/workflows/pipeline.yml`). Trigger it manually from the repo's
**Actions** tab → "AQI Hourly Pipeline" → "Run workflow". Each successful run
commits the newly collected raw files and the rebuilt clean CSV back to `main`.

Backfill (one-time, historical data) runs via
`.github/workflows/backfill.yml`, triggered manually from the Actions tab.

## Raw data volume
`data/raw/` contains one JSON file per city per hourly API call — currently
~31,400+ files covering 9 cities over a 5-month backfill window, plus new
files added hourly. GitHub's file browser truncates directory listings
beyond 1000 entries; clone the repo (`git clone ...`) to browse or verify
the full set locally, or check `data/clean/aqi_clean.csv` for the
consolidated, human-readable view.