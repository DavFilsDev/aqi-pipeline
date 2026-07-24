# Architecture

| Component        | Choice                          | Justification |
|-------------------|----------------------------------|----------------|
| Orchestrator       | GitHub Actions (scheduled workflow) | No server to maintain; free, reliable cron; run history doubles as proof of execution |
| Raw/clean storage  | Versioned in the Git repository (`data/raw/`, `data/clean/`) | GitHub Actions runners are ephemeral — the repo itself is the only persistent storage available |
| Data warehouse     | Neon (Postgres)                 | Free tier, serverless, reachable from anywhere without hosting a DB ourselves |
| Deployment         | None (no VM) — Actions runs on GitHub's infrastructure | Removes the need to manage Oracle Cloud/Docker; simpler for a 3-day project |

## Data flow
AQI API -> `scripts/extract/extract_aqi.py` -> `data/raw/*.json` (committed)
-> `scripts/transform/build_clean.py` -> `data/clean/aqi_clean.csv` (committed)
-> `scripts/load/load_warehouse.py` -> Neon (`dim_city`, `dim_time`, `fact_aqi`)

Runs hourly via `.github/workflows/pipeline.yml`. Each run commits the new raw file(s)
and the rebuilt clean CSV back to `main`, so the commit history on GitHub itself is
part of the audit trail (in addition to the Actions run history).