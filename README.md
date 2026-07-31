# AQI Pipeline

Automated pipeline collecting Air Quality Index (AQI) data for 9 cities, every hour,
24/7. Orchestrated with GitHub Actions, stored as versioned raw/clean files in this
repository, and loaded into a dimensional data warehouse hosted on Neon (Postgres).

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the stack and justification, and
[TASK.md](./TASK.md) for the team's task breakdown.

## Cities covered

9 cities: 4 international + 5 Malagasy.

| City | Country | Latitude | Longitude |
|---|---|---|---|
| Paris | France | 48.8566 | 2.3522 |
| Madrid | Spain | 40.4168 | -3.7038 |
| Buenos Aires | Argentina | -34.6037 | -58.3816 |
| London | England | 51.5074 | -0.1278 |
| Antananarivo | Madagascar | -18.8792 | 47.5079 |
| Toamasina | Madagascar | -18.1492 | 49.4023 |
| Antsirabe | Madagascar | -19.8659 | 47.0333 |
| Mahajanga | Madagascar | -15.7167 | 46.3167 |
| Fianarantsoa | Madagascar | -21.4527 | 47.0857 |

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
- **`dim_city`** — `city_id`, `city`, `country`, `latitude`, `longitude`. No measures.
- **`dim_time`** — `time_id`, `timestamp_utc`, `date`, `hour`, `day_of_week`,
  `is_weekend`. No measures.

Star schema chosen (no snowflaking): the two dimensions are small and flat, no
benefit from further normalization.

## Period covered & known gaps

- Backfill + live collection: 2026-02-25 04:00 UTC to 2026-07-31 04:00 UTC (hourly),
  for all 9 cities (~5 months, above the 3-month minimum). Continuous hourly
  collection continues via `pipeline.yml`.
- Coverage: 31,649 / 33,705 expected rows (9 cities × 3,745 hours) = **93.9%**
  (2,056 missing rows, fully explained by the two gaps below).
- Known gap 1 — sparse, API-side (1,174 hours, ~57% of the gap): a raw file exists
  but the OpenWeather history endpoint returned `200 OK` with an empty `list` (no
  measurement for that hour), spread across all 9 cities and several months.
  `build_clean.py` drops these rows rather than writing nulls, so they simply don't
  appear in `aqi_clean.csv` — the missing (city, hour) pairs are gaps, not corrupted
  rows.
- Known gap 2 — pipeline-side (882 hours, ~43% of the gap): no raw file at all exists
  for that hour. Exactly 98 hours per city, identical across all 9 cities, concentrated
  from 2026-07-25 onward (a ~25h outage on 2026-07-25/26, then several hours missing
  per day through 2026-07-31). Because it's identical across every city, it points to
  `pipeline.yml` runs failing or being skipped rather than an API issue — flagged to
  David (Task 1) to check the Actions run history.
- Fixed during QA (see RAPPORT.md for details): `build_clean.py` previously left
  measurement columns null for API calls with no data, and a pandas timestamp-parsing
  bug (`pd.to_datetime` inferring one format from the first row) was silently
  discarding ~400 valid rows per rebuild. Both are corrected; the coverage figures
  above are post-fix.

Expected row count in `fact_aqi` ≈ 9 cities × hours covered. The gap above explains
the discrepancy from a perfect 9 × hours count.

## Database connection (read-only, for grading)

- Host: `ep-blue-pine-asxselau-pooler.c-4.eu-central-1.aws.neon.tech`
- Database: `neondb`
- Read-only role: `readonly_ia1` (SELECT-only — see `sql/schema.sql` for the tables)
- Connection string:
  `postgresql://readonly_ia1:PassWord6%3F@ep-blue-pine-asxselau-pooler.c-4.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`

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
32,832 files covering 9 cities over a ~5-month window (2026-02-25 to
2026-07-31), plus new files added hourly. GitHub's file browser truncates directory listings
beyond 1000 entries; clone the repo (`git clone ...`) to browse or verify
the full set locally, or check `data/clean/aqi_clean.csv` for the
consolidated, human-readable view.