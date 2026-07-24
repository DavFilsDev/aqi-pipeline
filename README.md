# AQI Pipeline

Automated pipeline collecting Air Quality Index (AQI) data for 5 cities,
orchestrated with github Actions, loaded into a dimensional data warehouse (Neon/Postgres).

## Project structure
......

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
source .venv/bin/activate
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
(`.github/workflows/pipeline.yml`). You can also trigger it manually
from the repo's **Actions** tab -> "AQI Hourly Pipeline" -> "Run workflow".
Each run commits the newly collected raw files and the rebuilt clean CSV
back to `main`.