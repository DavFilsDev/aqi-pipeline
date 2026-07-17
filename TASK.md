# Task breakdown

Each task owner works on a `feature/<name>-<task>` branch and opens a PR into `main`.
Do not edit files outside your own folder without asking — see "Interfaces" below to avoid blocking each other.

## Shared interfaces (read this first — this is what lets everyone work in parallel)

- **Cities file**: `data/cities.json` — list of the 5 chosen cities with name, country, lat, lon.
  Created once (by task owner #2), then everyone reads from it. Do not hardcode city lists elsewhere.
- **Raw file naming convention**: `data/raw/<city_slug>_<YYYY-MM-DDTHH-MM-SS>.json`
  (e.g. `paris_2026-07-17T14-00-00.json`) — one file per city per API call, raw JSON, untouched.
- **Clean CSV columns** (draft — task #3 finalizes and documents exact units in README):
  `city, country, latitude, longitude, timestamp_utc, aqi, pm25, pm10, no2, o3` (add more if the API provides them)
- **Warehouse connection**: read from `NEON_DB_URL` env var — never hardcode credentials.

---

## Task 1 — Orchestration & infrastructure
**Owner:** David
**Folders:** `dags/`, `docker-compose.yml`, `Dockerfile`, deployment on Oracle Cloud

**Deliverables:**
- Working local Airflow (done)
- `dags/aqi_pipeline_dag.py` assembling everyone's tasks (extract per city -> transform -> load)
- Airflow deployed on the Oracle Cloud VM, running continuously with an hourly schedule

**Definition of done:** DAG runs end-to-end in the UI with all tasks green, on both local and the VM.

---

## Task 2 — API extraction
**Owner:** Fenohasina
**Folder:** `scripts/extract/`

**What you receive:** the 5 chosen cities (agree on them with the team today), an AQI API key in `.env`.

**What you deliver:**
- `data/cities.json` — the 5 cities with name, country, latitude, longitude
- `scripts/extract/extract_aqi.py` with a function `extract_aqi(city: dict) -> None` that:
  - calls the AQI API for one city
  - wraps the call in try/except (log the error, don't crash)
  - writes the raw JSON response to `data/raw/` following the naming convention above
- `scripts/extract/backfill.py` — same logic but replayable for historical dates (3-12 months), rejouable (can be re-run safely, e.g. skips a date/city if the raw file already exists)

**How to test it yourself (no Airflow needed):**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/extract/extract_aqi.py
ls data/raw/   # you should see one new JSON file per city
cat data/raw/<one_file>.json   # check it's valid, non-empty JSON with real AQI values
```
**Done when:** running the script produces 5 valid raw files (one per city), and running it twice in a row doesn't overwrite or corrupt anything (each call = new file).

---

## Task 3 — Transformation (raw -> clean)
**Owner:** Sarobidy
**Folder:** `scripts/transform/`

**What you receive:** raw JSON files in `data/raw/` (from task 2 — ask them for a few sample files today so you can start immediately without waiting).

**What you deliver:**
- `scripts/transform/build_clean.py` — reads ALL files in `data/raw/`, produces `data/clean/aqi_clean.csv`:
  - one row per city + per hour
  - sorted chronologically
  - deduplicated (same city + same hour = only one row, keep the most recent raw file if duplicates exist)
  - fully rebuilt from `raw/` every run (never append-only unless you handle dedup — rebuilding is simpler, do that)
- Exact column list + units documented (you'll add this to the storage README)

**How to test it yourself:**
```bash
# drop a few sample raw JSON files into data/raw/ manually first if task 2 isn't done yet
python scripts/transform/build_clean.py
head data/clean/aqi_clean.csv
wc -l data/clean/aqi_clean.csv   # sanity check row count
```
**Done when:** `aqi_clean.csv` has no duplicate (city, hour) pairs, is sorted, and running the script twice produces an identical file (idempotent).

---

## Task 4 — Data warehouse
**Owner:** Valisoa
**Folders:** `sql/`, `scripts/load/`

**What you receive:** a Neon connection string (create your own free Neon project today if you want to develop independently, then switch to the shared one later), and the `data/clean/aqi_clean.csv` column list from task 3 (ask them today for the draft columns so you're not blocked).

**What you deliver:**
- `sql/schema.sql` — star schema: `fact_aqi` (measures + FKs only, no descriptive columns), `dim_time` (date, hour, day_of_week, is_weekend), `dim_city` (name, country, lat, lon — no measures)
- `scripts/load/load_warehouse.py` — reads `data/clean/aqi_clean.csv`, upserts into `dim_city`/`dim_time`, inserts into `fact_aqi`. Must be rejouable (running it twice must not create duplicate fact rows).

**How to test it yourself:**
```bash
psql "$NEON_DB_URL" -f sql/schema.sql
python scripts/load/load_warehouse.py
psql "$NEON_DB_URL" -c "SELECT count(*) FROM fact_aqi;"
psql "$NEON_DB_URL" -c "SELECT * FROM fact_aqi LIMIT 5;"
```
**Done when:** row count in `fact_aqi` is roughly `cities × hours covered`, no measures appear in dimension tables, running the load script twice doesn't double the row count.

---

## Task 5 — Quality, docs, backfill, video
**Owner:** Zinedis
**Folders:** validation scripts, `README.md` (storage section), `RAPPORT.md`, video

**What you deliver:**
- `scripts/validate_clean.py` — checks `data/clean/aqi_clean.csv` against the data contract (no duplicates, no nulls in required columns, chronological order, one row per city per hour)
- Coordinates the backfill run (works with task 2) — confirms 3-12 months of history exists in `data/raw/` for all 5 cities
- Finalizes `README.md`: cities + lat/lon, exact columns + units in `clean/`, warehouse schema diagram, period covered, known gaps, DB connection info
- `RAPPORT.md`: team working method, task split (link to this file), difficulties + solutions, justified technical choices
- 3-minute demo video: pipeline running -> storage zones -> a SQL query on the warehouse

**How to test it yourself:**
```bash
python scripts/validate_clean.py   # should print PASS or a clear list of violations
```
**Done when:** validation script passes with zero errors, and all four docs are readable by someone outside the team without needing to ask questions.