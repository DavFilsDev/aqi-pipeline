# AQI Pipeline

Automated pipeline collecting Air Quality Index (AQI) data for 5 cities,
orchestrated with Apache Airflow, loaded into a dimensional data warehouse (Neon/Postgres).

## Project structure

- `dags/` — Airflow DAGs
- `scripts/extract/` — API extraction logic (per-city)
- `scripts/transform/` — raw/ -> clean/ transformation
- `scripts/load/` — load_warehouse.py and warehouse loading logic
- `data/raw/` — raw untouched files (git-ignored, kept on the deployment host)
- `data/clean/` — single rebuilt CSV (versioned)
- `sql/` — warehouse schema and validation queries

## Local setup (Windows / macOS / Linux)

### 1. Install Docker
- **Windows**: install Docker Desktop (enable WSL2 when prompted). Use the WSL terminal or PowerShell for the commands below.
- **Ubuntu/Debian**: `sudo apt install docker.io docker-compose-plugin`, then `sudo usermod -aG docker $USER` and log back in.

### 2. Clone and configure
```bash
git clone https://github.com/<org>/aqi-pipeline.git
cd aqi-pipeline
cp .env.example .env
```
Fill in `.env` with your own AQI API key. Ask the team for the Neon connection string (or use your own dev Neon branch).

On Linux/macOS only, set your user ID to avoid file permission issues:
```bash
echo "AIRFLOW_UID=$(id -u)" >> .env
```
(Windows users: leave the default `AIRFLOW_UID=50000` in `.env.example`.)

### 3. Start Airflow
```bash
docker compose up -d --build
```
First start takes a few minutes (image build + Airflow DB init).

### 4. Open the UI
Go to http://localhost:8080 — login `admin` / `admin`.
You should see the `hello_etl` DAG. Unpause it and trigger it manually to confirm your setup works (check the logs of each task).

### 5. Develop
- Add your DAG file in `dags/` — it appears in the UI within ~30 seconds.
- Add your extraction/transform/load logic in the matching `scripts/` subfolder.
- You can also test scripts standalone (outside Airflow) with a local virtualenv:
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/extract/your_script.py
```

### 6. Stop
```bash
docker compose down        # stop containers, keep data
docker compose down -v     # stop and wipe Airflow's internal DB (reset)
```

## Data contract (clean/)
TODO — filled in by the transformation owner: exact columns, units, cities with lat/lon.

## Warehouse schema
TODO — filled in by the warehouse owner: star schema description.