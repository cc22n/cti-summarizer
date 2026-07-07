# CTI Summarizer + Trend Predictor

## Project Overview
Threat intelligence platform that ingests public CTI feeds (NVD, CISA KEV, AlienVault OTX, MITRE ATT&CK, RSS blogs), generates executive summaries via LLM, and predicts threat trends with time series models. FastAPI backend + React SPA frontend.

**Repo:** https://github.com/cc22n/cti-summarizer
**Author:** Enrique
**Status:** ALL PHASES COMPLETE

---

## Critical Constraints (ALWAYS FOLLOW)
- **Windows/PowerShell environment** - All Python files MUST use pure ASCII only. No accents, tildes, emojis, or special characters in code.
- **psycopg v3 ONLY** - Never use psycopg2 (encoding bug on this Windows setup). Import as `psycopg`, connection string uses `postgresql+psycopg://`.
- **pip flag** - Always use `--break-system-packages` for pip installs.
- **Project path:** `C:\Users\coral\Desktop\cti-summarizer`
- **TypeScript build** - Always use `tsc -b` (project references), NOT `tsc --noEmit`. The root `tsconfig.json` has `files: []` so `tsc --noEmit` silently skips all files.
- **TanStack Query retry callbacks** - Do NOT annotate `error` as `unknown` in `retry` callbacks — it breaks TData inference and makes `data` resolve as `unknown`, causing cascading JSX type errors.

---

## Tech Stack
| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11+) |
| Database | PostgreSQL (psycopg v3) |
| ORM | SQLAlchemy 2.x (mapped_column style) |
| Migrations | Alembic |
| Task Queue | Celery + Redis |
| Cache | Redis |
| LLM | Grok 4.1 Fast (xAI) via OpenAI-compatible SDK (openai==1.58.1) |
| ML | Prophet 1.1.6 (rolling average fallback for sparse data) |
| Frontend | React 19 + Vite 8 + TypeScript 5.9 + Recharts 3 + TanStack Query v5 |
| Styling | Tailwind CSS v4 (@tailwindcss/vite plugin) |
| Testing | pytest + httpx (SQLite in-memory for tests) |
| HTTP Client | httpx (async) |

---

## Development Phases
- [x] **Fase 1:** Ingestion + Normalization (NVD + CISA KEV) + FastAPI + Tests
- [x] **Fase 2:** OTX + MITRE ATT&CK + RSS adapters + Grok 4.1 Fast summarization
- [x] **Fase 3:** React SPA dashboard (Vite + TypeScript + Recharts)
- [x] **Fase 4:** Time series prediction with Prophet (14-day forecast, 6 series)

---

## Project Structure
```
cti-summarizer/
|-- alembic/
|   |-- versions/
|   |   |-- 001_add_summaries_table.py
|   |   |-- 002_add_trend_predictions_table.py
|   |-- env.py
|-- app/
|   |-- main.py                 # FastAPI entry point
|   |-- config.py               # pydantic-settings (extra="ignore" for unknown .env vars)
|   |-- database.py             # Engine, SessionLocal, Base, get_db
|   |-- celery_app.py           # Celery configuration
|   |-- models/
|   |   |-- source.py
|   |   |-- alert.py            # RawAlert + NormalizedAlert
|   |   |-- category.py         # AlertCategory + alert_category_map
|   |   |-- ingestion_log.py
|   |   |-- summary.py          # LLM summaries (Fase 2)
|   |   |-- trend_prediction.py # ML predictions (Fase 4)
|   |-- schemas/
|   |   |-- alert.py
|   |   |-- source.py
|   |   |-- dashboard.py
|   |   |-- summary.py
|   |   |-- prediction.py       # Decimal->float via @field_serializer
|   |-- api/v1/
|   |   |-- __init__.py         # Aggregates all routers
|   |   |-- alerts.py
|   |   |-- sources.py
|   |   |-- dashboard.py
|   |   |-- summaries.py        # /digest/latest declared BEFORE /{id} to avoid routing conflict
|   |   |-- predictions.py
|   |-- services/
|   |   |-- ingestion/
|   |   |   |-- base_adapter.py
|   |   |   |-- nvd_adapter.py
|   |   |   |-- cisa_adapter.py
|   |   |   |-- otx_adapter.py  # 500-alert cap, X-OTX-API-KEY header
|   |   |   |-- mitre_adapter.py# Downloads ~40MB STIX bundle, filters attack-pattern objects
|   |   |   |-- rss_adapter.py  # feedparser via run_in_executor (non-blocking)
|   |   |-- normalization.py    # Dispatches to _normalize_nvd/cisa/otx/mitre/rss
|   |   |-- ingestion_orchestrator.py
|   |   |-- summarization_service.py  # AsyncOpenAI client, alert + digest summaries
|   |   |-- prediction_service.py     # Prophet with rolling_avg fallback, deferred import
|   |-- workers/
|       |-- ingestion_tasks.py  # All 5 adapters + Beat schedule
|       |-- summary_tasks.py    # summarize_alerts + generate_daily_digest
|       |-- prediction_tasks.py # run_prediction_task (max_retries=1, countdown=300)
|-- frontend/
|   |-- src/
|   |   |-- types/              # alert.ts, dashboard.ts, source.ts, summary.ts, prediction.ts
|   |   |-- services/           # api.ts (axios), dashboard.ts, alerts.ts, sources.ts,
|   |   |                       # summaries.ts, predictions.ts
|   |   |-- hooks/              # useDashboard, useAlerts, useSources, useSummaries,
|   |   |                       # usePredictions
|   |   |-- lib/                # chartUtils.ts, formatters.ts
|   |   |-- components/
|   |   |   |-- layout/         # Layout, Header, Sidebar
|   |   |   |-- common/         # LoadingSpinner, StatCard, AlertBadge
|   |   |   |-- dashboard/      # TimelineChart, SeverityPieChart, SourceBarChart
|   |   |   |-- predictions/    # PredictionChart (ComposedChart: solid + dashed lines)
|   |   |-- pages/              # DashboardPage, AlertsPage, AlertDetailPage,
|   |                           # SourcesPage, SummariesPage, PredictionsPage
|   |-- tsconfig.json           # Project references root (files: [])
|   |-- tsconfig.app.json       # Strict app config (noUnusedLocals, verbatimModuleSyntax)
|   |-- tsconfig.node.json      # Vite config
|   |-- vite.config.ts
|-- scripts/
|   |-- setup_db.py             # Create DB + tables + seed 8 sources + run alembic upgrade
|   |-- run_ingestion.py
|-- tests/
|   |-- conftest.py
|   |-- test_adapters/
|   |-- test_services/
|   |-- test_api/
```

---

## Database Schema (8 tables)
1. **sources** - CTI feed sources (NVD, CISA_KEV, OTX, MITRE_ATTACK, RSS)
2. **raw_alerts** - Raw ingested data as JSONB
3. **normalized_alerts** - Unified format with severity, CVSS, IOCs, etc.
4. **alert_categories** - Threat categories (ransomware, rce, phishing, etc.)
5. **alert_category_map** - M2M between alerts and categories
6. **ingestion_logs** - Tracks each polling run per source
7. **summaries** - LLM-generated summaries (alert or digest type)
8. **trend_predictions** - Prophet forecast rows (run_id, series_key, target_date, predicted/lower/upper)

---

## API Endpoints (All Implemented)

### Core
- `GET /health`
- `GET /api/v1/alerts` - paginated, filterable by severity/source/search
- `GET /api/v1/alerts/{id}`
- `GET /api/v1/alerts/stats`
- `GET /api/v1/sources`
- `GET /api/v1/sources/{id}/health`
- `POST /api/v1/sources/{id}/poll`
- `GET /api/v1/dashboard/overview`
- `GET /api/v1/dashboard/timeline`

### Summaries (Fase 2)
- `GET /api/v1/summaries`
- `GET /api/v1/summaries/digest/latest`  ← must be declared BEFORE `/{id}`
- `GET /api/v1/summaries/{id}`
- `POST /api/v1/summaries/summarize`
- `POST /api/v1/summaries/digest`

### Predictions (Fase 4)
- `GET /api/v1/predictions/latest` - latest run with all series
- `POST /api/v1/predictions/generate` - triggers Celery task

---

## Celery Beat Schedule
| Task | Interval |
|---|---|
| ingest-nvd | Every 6h |
| ingest-cisa-kev | Every 24h |
| ingest-otx | Every 6h |
| ingest-mitre-attack | Weekly |
| ingest-rss | Every 2h |
| generate-daily-digest | Every 24h |
| predict-trends-weekly | Weekly |

---

## Ingestion Pipeline Flow
```
Adapter.fetch_alerts(since) -> list[RawAlertData]
    |
    v
IngestionOrchestrator.run(adapter)
    |-- Ensure Source exists in DB
    |-- Fetch raw alerts via adapter
    |-- Deduplicate by (source_id, external_id)
    |-- Store new RawAlerts
    |-- Normalize each -> NormalizedAlert
    |-- Log result to IngestionLog
    |-- Update Source.last_polled_at
```

---

## Normalization Rules
### NVD:
- CVSS: tries v3.1 -> v3.0 -> v2.0
- Severity: >=9.0 critical, >=7.0 high, >=4.0 medium, >0 low, else info

### CISA KEV:
- Ransomware campaign = critical, else high

### OTX:
- indicator_count >= 50 -> high, >= 10 -> medium, else low
- Ransomware tag -> critical override

### MITRE ATT&CK:
- Always "info" (technique reference, not active threat)

### RSS:
- Always "info"

---

## Prediction Service Design
- **SERIES_KEYS**: `["critical", "high", "medium", "low", "info", "total"]`
- **Lookback**: 90 days of historical alerts
- **Forecast**: 14 days ahead
- **Effective date**: `COALESCE(published_date, normalized_at)`
- **Prophet**: imported inside `_fit_prophet()` (deferred import — backend starts without prophet installed)
- **Fallback**: rolling 7-day average when < 10 non-zero days in series
- **Storage**: one row per `(run_id, series_key, target_date)`, unique index
- **Decimals**: `Numeric(10,2)` in DB, serialized to float via `@field_serializer`

---

## Running the Project
```powershell
# 1. Setup
cd C:\Users\coral\Desktop\cti-summarizer
pip install -r requirements.txt --break-system-packages
copy .env.example .env  # Edit with your API keys

# 2. Database
python -m scripts.setup_db

# 3. API
uvicorn app.main:app --reload

# 4. Frontend
cd frontend && npm install && npm run dev

# 5. Celery worker (separate terminal)
celery -A app.celery_app worker --loglevel=info

# 6. Celery Beat (separate terminal)
celery -A app.celery_app beat --loglevel=info

# 7. Run tests
pytest -v --tb=short
```

---

## Key Design Decisions
1. **Adapter pattern** - each CTI source has its own adapter inheriting BaseAdapter
2. **Raw + Normalized** two-stage storage - preserves originals, enables unified queries
3. **Deduplication** by `(source_id, external_id)` prevents duplicate ingestion
4. **SQLite for tests** - fast, no external deps, auto-created/destroyed per test
5. **Celery Beat** for all scheduled tasks
6. **tenacity** retry with exponential backoff on all HTTP calls
7. **Deferred Prophet import** - `from prophet import Prophet` inside function so backend starts even if prophet not installed
8. **`/digest/latest` before `/{id}`** in FastAPI router to avoid routing conflict
9. **`extra="ignore"` in pydantic Settings** - tolerates unknown keys in `.env` file
10. **`cvss_score` typed as `string | null` in frontend** - Decimal serializes as string from FastAPI

---

## Testing
Tests use SQLite in-memory with auto-created tables per test.
Adapters are tested with mocked httpx responses.
API tests use FastAPI TestClient with overridden DB dependency.

Run: `pytest -v --tb=short`
Run with coverage: `pytest --cov=app --cov-report=html`

---

## Environment Variables (.env)
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cti_summarizer
REDIS_URL=redis://localhost:6379/0
NVD_API_KEY=your_key
OTX_API_KEY=your_key
XAI_API_KEY=your_key
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
```
