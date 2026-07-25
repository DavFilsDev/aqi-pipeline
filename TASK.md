# Task breakdown

Each task owner works on a `feature/<name>-<task>` branch and opens a PR into `main`.
Do not edit files outside your own folder without asking — see "Interfaces" below to avoid blocking each other.

## Shared interfaces (read this first — this is what lets everyone work in parallel)

- **Cities file**: `data/cities.json` — 9 cities (name, country, lat, lon): Paris, Madrid,
  Buenos Aires, London, and 5 Malagasy cities (Antananarivo, Toamasina, Antsirabe,
  Mahajanga, Fianarantsoa). Everyone reads from this file — never hardcode a city list
  elsewhere.
- **Raw file naming convention**: `data/raw/<city_slug>_<YYYY-MM-DDTHH-MM-SS>.json`
  (e.g. `paris_2026-07-17T14-00-00.json`) — one file per city per API call, raw JSON,
  untouched. **This folder is versioned in Git** (not git-ignored) — it is the only
  persistent storage available since GitHub Actions runners are ephemeral.
- **Clean CSV columns**: `city, country, latitude, longitude, timestamp_utc, aqi, pm25,
  pm10, no2, o3` — finalized, documented with units in `README.md`.
- **Secrets**: `AQI_API_KEY` and `NEON_DB_URL` — stored locally in `.env` (never
  committed) AND as GitHub Actions repository secrets (Settings → Secrets and
  variables → Actions), used by the workflows in `.github/workflows/`.
- **Orchestrator**: GitHub Actions, not Airflow/Docker/Oracle Cloud (migration
  completed — see `ARCHITECTURE.md`). No DAGs; workflows are sequential YAML steps.

---

## Task 1 — Orchestration & CI/CD
**Owner:** David
**Folders:** `.github/workflows/`

**Deliverables:**
- `.github/workflows/pipeline.yml` — hourly cron (`5 * * * *`): extract → build clean →
  validate → load warehouse → commit & push raw/clean data back to `main`
- `.github/workflows/backfill.yml` — manual (`workflow_dispatch`) historical run
- Concurrency handled per-workflow (separate groups) with retry-on-push-conflict
  (fetch + rebase) to avoid races between the two workflows
- GitHub repo settings configured: Actions → workflow permissions set to
  "Read and write", both secrets added

**Definition of done:** the hourly workflow appears in the Actions run history with
successful runs at least 5 hours apart with nobody watching, and each successful run
produces a new commit on `main`.

---

## Task 2 — API extraction
**Owner:** Fenohasina
**Folder:** `scripts/extract/`, `data/cities.json`

**What you deliver:**
- `data/cities.json` — 9 cities with name, country, latitude, longitude (done)
- `scripts/extract/extract_aqi.py` — calls the AQI API for one city, try/except per
  call (logs the error, never crashes the whole run), writes raw JSON to `data/raw/`
- `scripts/extract/backfill.py` — same logic, replayable over a historical window
  (`BACKFILL_MONTHS`, currently set to 5 — within the 3-12 month range required),
  idempotent (skips a date/city if the raw file already exists)

**How to test it yourself:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/extract/extract_aqi.py
ls data/raw/   # one new JSON file per city
```

**Done when:** running the script twice never overwrites or corrupts a file (each call
= a new, uniquely-named file).

---

## Task 3 — Transformation (raw -> clean)
**Owner:** Sarobidy
**Folder:** `scripts/transform/`

**What you deliver:**
- `scripts/transform/build_clean.py` — reads every file in `data/raw/` (parses the
  OpenWeather `list[0].main.aqi` / `list[0].components.*` structure), rebuilds
  `data/clean/aqi_clean.csv` from scratch every run: one row per city+hour, sorted
  chronologically, deduplicated (city+hour, keeps the most recent raw file on conflict)
- `scripts/transform/validate_clean.py` *(also referenced in Task 5 — same file, single
  source of truth)*

**How to test it yourself:**
```bash
python scripts/transform/build_clean.py
head data/clean/aqi_clean.csv
wc -l data/clean/aqi_clean.csv
```

**Done when:** no duplicate (city, hour) pairs, correctly sorted, and running the
script twice on the same `data/raw/` produces an identical file (idempotent).

---

## Task 4 — Data warehouse
**Owner:** Valisoa
**Folders:** `sql/`, `scripts/load/`

**What you deliver:**
- `sql/schema.sql` — star schema: `fact_aqi` (measures + FKs only), `dim_time` (date,
  hour, day_of_week, is_weekend), `dim_city` (name, country, lat, lon) — no measures in
  dimensions, no descriptive columns in the fact table
- `scripts/load/load_warehouse.py` — reads `data/clean/aqi_clean.csv`, upserts into
  `dim_city`/`dim_time`/`fact_aqi` using `execute_values(..., fetch=True)` (important:
  `fetch=True` is required so `RETURNING` captures every page of a large batch, not
  just the last one — this caused a KeyError bug before it was fixed)

**How to test it yourself:**
```bash
psql "$NEON_DB_URL" -f sql/schema.sql
python scripts/load/load_warehouse.py
psql "$NEON_DB_URL" -c "SELECT count(*) FROM fact_aqi;"
```

**Done when:** row count in `fact_aqi` ≈ `9 cities × hours covered`, no measures in
dimension tables, running the load script twice doesn't change the row count.

---

## Task 5 — Quality, docs, backfill, video
**Owner:** Zinedis
**Folders:** `scripts/transform/validate_clean.py`, `README.md`, `RAPPORT.md`, video

**What you deliver:**
- `scripts/transform/validate_clean.py` *(note: lives under `scripts/transform/`, not
  `scripts/`)* — checks `data/clean/aqi_clean.csv` against the data contract (no
  duplicates, no nulls in required columns, chronological order, one row per city+hour)
- Confirms the 5-month backfill completed for all 9 cities in `data/raw/`
- Finalizes `README.md`: cities + lat/lon, exact columns + units, warehouse schema,
  period covered, known gaps, read-only DB connection info
- `RAPPORT.md`: team working method, task split, difficulties + solutions (including
  the Docker DNS issue and the Airflow→GitHub Actions migration), technical choices
- 3-minute demo video: **use the GitHub Actions run history and the automatic commit
  history on `main` as proof of automated runs** (replaces the Airflow UI screenshots
  originally planned) → pipeline running → storage zones (`data/raw`, `data/clean`) →
  a SQL query on the warehouse

**How to test it yourself:**
```bash
python scripts/transform/validate_clean.py
```

**Done when:** validation passes with zero errors, and all docs are readable by
someone outside the team without needing to ask questions.