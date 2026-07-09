# CTI Summarizer + Trend Predictor

## Project Overview
Threat intelligence platform that ingests public CTI feeds (NVD, CISA KEV, AlienVault OTX, MITRE ATT&CK, RSS blogs, URLhaus, VirusTotal), generates executive summaries via LLM, predicts threat trends with time series models, and provides semantic search, correlation analysis, and real-time alert streaming. FastAPI backend + React SPA frontend with JWT auth.

**Repo:** https://github.com/cc22n/cti-summarizer
**Author:** Enrique
**Status:** ALL PHASES COMPLETE (plus post-release hardening: auth, WebSocket, exports, semantic search, observability)

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
| Database | PostgreSQL (psycopg v3, sync + native async sessions) |
| ORM | SQLAlchemy 2.x (mapped_column style) |
| Migrations | Alembic (9 revisions) |
| Task Queue | Celery + Redis |
| Cache / PubSub | Redis (stats cache, login lockout, WebSocket fan-out) |
| Auth | JWT (python-jose) + bcrypt (passlib), legacy X-API-Key fallback |
| Rate limiting | slowapi |
| Observability | prometheus-client (/metrics), python-json-logger (JSON logs in prod) |
| LLM | Grok 4.1 Fast (xAI) via OpenAI-compatible SDK (openai==1.58.1) |
| Embeddings | xAI embeddings for semantic search (ILIKE fallback) |
| ML | Prophet 1.1.6 (rolling average fallback for sparse data) |
| Frontend | React 19 + Vite 8 + TypeScript 5.9 + Recharts 3 + TanStack Query v5 + react-router |
| Styling | Tailwind CSS v4 (@tailwindcss/vite plugin) |
| Testing (backend) | pytest + httpx (SQLite in-memory) — 278 tests |
| Testing (frontend) | Vitest (70 unit tests) + Playwright e2e (17 tests in frontend/e2e/) |
| HTTP Client | httpx (async) |

---

## Project Structure
```
cti-summarizer/
|-- alembic/versions/           # 001 summaries ... 009 dedup constraint + category index
|-- app/
|   |-- main.py                 # FastAPI entry: CORS, rate limiter, metrics, security
|   |                           # headers, sanitized error handlers, /health, /metrics
|   |-- config.py               # pydantic-settings (extra="ignore")
|   |-- database.py             # Sync engine + native async engine (psycopg v3)
|   |-- dependencies.py         # require_api_key: JWT Bearer > X-API-Key > dev bypass
|   |-- limiter.py              # slowapi limiter
|   |-- cache.py                # Redis cache helpers (graceful when Redis is down)
|   |-- metrics.py              # Prometheus middleware + registry
|   |-- celery_app.py           # Celery config; Beat schedule lives in ingestion_tasks.py
|   |-- auth/                   # jwt.py (tokens+bcrypt), lockout.py (Redis), dependencies.py
|   |-- middleware/             # security_headers.py
|   |-- models/                 # source, alert, category, ingestion_log, summary,
|   |                           # trend_prediction, user
|   |-- schemas/                # + user.py; prediction.py serializes Decimal->float
|   |-- api/v1/
|   |   |-- alerts.py           # list/detail/stats/export CSV+STIX/semantic-search/
|   |   |                       # correlations/notes/acknowledge
|   |   |-- auth.py             # login (lockout), me, register (admin), users (admin)
|   |   |-- categories.py
|   |   |-- dashboard.py
|   |   |-- predictions.py      # latest, generate, tasks/{task_id} polling
|   |   |-- sources.py          # list, health, logs, toggle, poll
|   |   |-- summaries.py        # /digest/latest declared BEFORE /{id}
|   |   |-- ws.py               # WebSocket /ws/alerts (Redis Pub/Sub relay)
|   |-- services/
|   |   |-- ingestion/          # base, nvd, cisa, otx, mitre, rss, urlhaus, virustotal
|   |   |-- normalization.py
|   |   |-- ingestion_orchestrator.py  # dedup + webhook + Redis publish on critical/high
|   |   |-- summarization_service.py   # Grok; XML-tagged untrusted content in prompts
|   |   |-- prediction_service.py      # Prophet, deferred import, rolling_avg fallback
|   |   |-- embedding_service.py       # semantic_rank for /semantic-search
|   |   |-- notification_service.py    # fire-and-forget webhook (WEBHOOK_URL)
|   |   |-- email_service.py           # SMTP weekly executive report
|   |   |-- elasticsearch_service.py   # ES/Logstash event forwarding
|   |-- workers/                # ingestion_tasks (+ Beat schedule), summary_tasks,
|                               # prediction_tasks, search_tasks, utils
|-- frontend/
|   |-- src/
|   |   |-- App.tsx             # React.lazy per page + Suspense (code splitting);
|   |   |                       # RequireAuth / RequireAdmin route guards;
|   |   |                       # RouteError as errorElement at every route level
|   |   |-- contexts/           # AuthContext (JWT session), SidebarContext
|   |   |-- types/ services/ hooks/  # incl. useRealtimeAlerts (WebSocket),
|   |   |                            # useDebouncedValue, useUsers, useCategories
|   |   |-- components/         # layout/ common/ dashboard/ alerts/ sources/
|   |   |                       # summaries/ predictions/
|   |   |-- pages/              # Dashboard, Alerts, AlertDetail, Sources, Summaries,
|   |                           # Predictions, Correlations, SemanticSearch, Admin,
|   |                           # Login, NotFound
|   |-- e2e/                    # Playwright specs: login, dashboard, not-found,
|   |                           # alerts-flow (filter/pagination/acknowledge/crash
|   |                           # fallback); fixtures.ts exposes mockAppApi()
|   |-- tsconfig.json           # Project references root (files: [])
|-- scripts/                    # setup_db.py, run_ingestion.py, manage_users.py
|-- tests/                      # test_adapters/ test_api/ test_services/ test_workers/
```

---

## Database Schema (9 tables)
1. **sources** - CTI feed sources (NVD, CISA_KEV, OTX, MITRE_ATTACK, RSS, URLHAUS, VIRUSTOTAL)
2. **raw_alerts** - Raw ingested data as JSONB; unique constraint (source_id, external_id)
3. **normalized_alerts** - Unified format: severity, CVSS, IOCs, embedding, is_anomaly, notes, is_acknowledged/acknowledged_at, fulltext GIN index
4. **alert_categories** - Threat categories (ransomware, rce, phishing, etc.)
5. **alert_category_map** - M2M between alerts and categories
6. **ingestion_logs** - Tracks each polling run per source
7. **summaries** - LLM-generated summaries (alert or digest type)
8. **trend_predictions** - Prophet forecast rows (run_id, series_key, target_date, predicted/lower/upper)
9. **users** - JWT auth accounts (username, bcrypt hash, role admin/analyst, is_active)

---

## API Endpoints

### Auth (JWT)
- `POST /api/v1/auth/login` - rate-limited 5/min; 15-min lockout after 5 failures (Redis)
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/register` - admin only
- `GET /api/v1/auth/users` - admin only

### Alerts
- `GET /api/v1/alerts` - pagination, filters (severity/source/search/category/dates/is_acknowledged), sorting. `sort_by=severity` sorts by threat rank (SQL CASE), not alphabetically. Fulltext tsvector search on PostgreSQL, ILIKE fallback on SQLite.
- `GET /api/v1/alerts/stats` - cached 60s in Redis
- `GET /api/v1/alerts/export?format=csv|stix` - CSV output is formula-injection-safe (`_csv_safe` prefixes `'` to leading =,+,-,@); STIX 2.1 bundle streamed
- `GET /api/v1/alerts/semantic-search` - xAI embeddings ranking, text fallback (async session)
- `GET /api/v1/alerts/correlations` - group by shared CVE/vendor, rate-limited 5/min
- `PATCH /api/v1/alerts/{id}/notes` - write-guarded
- `PATCH /api/v1/alerts/{id}/acknowledge` - write-guarded, toggle
- `GET /api/v1/alerts/{id}`

### Sources / Dashboard / Categories
- `GET /api/v1/sources`, `GET /{id}/health`, `GET /{id}/logs`, `PATCH /{id}/toggle`, `POST /{id}/poll`
- `GET /api/v1/dashboard/overview`, `GET /api/v1/dashboard/timeline`
- `GET /api/v1/categories`

### Summaries
- `GET /api/v1/summaries`
- `GET /api/v1/summaries/digest/latest`  <- must stay declared BEFORE `/{id}`
- `GET /api/v1/summaries/{id}`
- `POST /api/v1/summaries/generate`
- `POST /api/v1/summaries/digest/generate`

### Predictions
- `GET /api/v1/predictions/latest`
- `POST /api/v1/predictions/generate` - triggers Celery task
- `GET /api/v1/predictions/tasks/{task_id}` - Celery task status polling

### Infra
- `GET /health` - deep check (DB 503 on failure, Redis degrades to 200/degraded)
- `GET /metrics` - Prometheus; localhost-only in production
- `WS /ws/alerts` - streams new critical/high alerts via Redis Pub/Sub; concurrent client-frame watcher releases dead connections immediately

**Auth model:** write endpoints (POST/PATCH) require JWT Bearer or legacy X-API-Key (timing-safe compare); GET endpoints are public. If neither JWT_SECRET_KEY nor API_KEY is configured, dev bypass is active.

---

## Celery Beat Schedule (defined in app/workers/ingestion_tasks.py)
| Task | Schedule |
|---|---|
| ingest-nvd | Every 6h (00,06,12,18 UTC) |
| ingest-cisa-kev | Daily 07:00 |
| ingest-otx | Every 6h (01:30,07:30,13:30,19:30) |
| ingest-mitre-attack | Weekly Mon 02:00 |
| ingest-rss | Every 2h |
| ingest-urlhaus | Every 4h |
| ingest-virustotal | Daily 04:30 |
| generate-daily-digest | Daily 08:00 |
| predict-trends-weekly | Weekly Mon 03:00 |
| send-weekly-report | Weekly Mon 09:00 (SMTP) |
| forward-to-elasticsearch | Hourly at :15 (2h lookback) |

---

## Ingestion Pipeline Flow
```
Adapter.fetch_alerts(since) -> list[RawAlertData]
    |
    v
IngestionOrchestrator.run(adapter)
    |-- Ensure Source exists in DB
    |-- Fetch raw alerts via adapter
    |-- Deduplicate by (source_id, external_id)  [in-process set + DB unique constraint]
    |-- Store new RawAlerts -> Normalize -> assign categories
    |-- Webhook + Redis Pub/Sub publish on new critical/high alerts
    |-- Log result to IngestionLog; update Source.last_polled_at
    |-- Webhook on 3 consecutive ingestion failures
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

### MITRE ATT&CK / RSS:
- Always "info"

### URLhaus / VirusTotal:
- Malicious URL / IOC enrichment feeds (see adapters for severity mapping)

---

## Prediction Service Design
- **SERIES_KEYS**: `["critical", "high", "medium", "low", "info", "total"]`
- **Lookback**: 90 days; **Forecast**: 14 days
- **Effective date**: `COALESCE(published_date, normalized_at)`
- **Prophet**: imported inside `_fit_prophet()` (deferred — backend starts without prophet)
- **Fallback**: rolling 7-day average when < 10 non-zero days in series
- **Anomaly flag**: is_anomaly column (migration 004)
- **Storage**: one row per `(run_id, series_key, target_date)`, unique index
- **Decimals**: `Numeric(10,2)` in DB, serialized to float via `@field_serializer`

---

## Security Hardening (implemented)
- JWT auth with bcrypt hashing; admin-only user registration; login lockout in Redis
- Timing-safe X-API-Key comparison (hmac.compare_digest)
- LLM prompt injection defense: feed content wrapped in XML tags + system prompt marks it untrusted
- CSV export formula-injection sanitization (`_csv_safe` in api/v1/alerts.py)
- Sanitized 422/500 error responses in production (no field names / stack traces)
- Security headers middleware; /metrics restricted to localhost in production
- Rate limiting on login (5/min), export (10/min), correlations (5/min)
- Secrets: only .env.example files in git; .env ignored

---

## Running the Project
```powershell
# 1. Setup
cd C:\Users\coral\Desktop\cti-summarizer
pip install -r requirements.txt --break-system-packages
copy .env.example .env  # Edit with your API keys

# 2. Database
python -m scripts.setup_db
python -m scripts.manage_users  # create admin user for JWT auth

# 3. API
uvicorn app.main:app --reload

# 4. Frontend
cd frontend && npm install && npm run dev

# 5. Celery worker + Beat (separate terminals)
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info

# 6. Tests
pytest -v --tb=short          # backend (278 tests)
cd frontend && npm test        # Vitest unit tests (70)
cd frontend && npm run e2e     # Playwright e2e
```

---

## Key Design Decisions
1. **Adapter pattern** - each CTI source has its own adapter inheriting BaseAdapter (7 adapters)
2. **Raw + Normalized** two-stage storage - preserves originals, enables unified queries
3. **Deduplication** by `(source_id, external_id)` - in-process check + DB unique constraint as safety net for concurrent workers
4. **SQLite for tests** - fast, no external deps; code branches on dialect (tsvector vs ILIKE)
5. **Celery Beat** for all scheduled tasks; Beat schedule lives in `ingestion_tasks.py`
6. **tenacity** retry with exponential backoff on all HTTP calls
7. **Deferred Prophet import** - backend starts even if prophet not installed
8. **`/digest/latest` before `/{id}`** in FastAPI router to avoid routing conflict
9. **`extra="ignore"` in pydantic Settings** - tolerates unknown keys in `.env`
10. **`cvss_score` typed as `string | null` in frontend** - Decimal serializes as string from FastAPI
11. **Unified write guard** (`require_api_key`): JWT Bearer > X-API-Key > dev bypass
12. **Graceful degradation** - Redis down = no cache/lockout/WS but API keeps working; missing API keys log warnings instead of crashing
13. **React.lazy code splitting** - initial bundle 298 KB; Recharts (356 KB) loads only on chart pages; LoginPage stays eager
14. **WebSocket disconnect watcher** - concurrent task drains client frames so dead connections release Redis subscriptions immediately
15. **Route-level errorElement (RouteError)** - the app-level ErrorBoundary never sees route render errors (React Router catches them first); a pathless wrapper inside Layout's children renders the fallback with the sidebar intact

---

## Testing
- Backend: SQLite in-memory, tables auto-created per test; adapters mocked with httpx; API via TestClient with overridden DB dependency. 278 tests.
- Frontend: Vitest (components, pages, hooks — 70 tests) + Playwright e2e in `frontend/e2e/` (17 tests: headings/login/404 plus alert flows — severity filter, pagination, acknowledge, crash fallback). test-results/ and playwright-report/ are gitignored.
- Playwright gotchas: mocks must return correctly shaped payloads (pages dereference response fields and a bare `{}` crashes them into the error fallback); the LAST registered `page.route` wins, so register broad patterns before specific ones; `workers: 1` because parallel workers race the Vite dev server's on-demand transform of lazy chunks.
- Run: `pytest -v --tb=short` | coverage: `pytest --cov=app --cov-report=html`

---

## Environment Variables (.env)
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cti_summarizer
REDIS_URL=redis://localhost:6379/0
NVD_API_KEY=your_key
OTX_API_KEY=your_key
XAI_API_KEY=your_key
VIRUSTOTAL_API_KEY=your_key
APP_ENV=development            # "production" enables JSON logs, sanitized errors,
                               # localhost-only /metrics
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173
API_KEY=                       # legacy write-guard key (optional)
JWT_SECRET_KEY=                # enables JWT auth; empty = dev bypass
WEBHOOK_URL=                   # Slack/Discord/n8n notifications (optional)
SMTP_HOST= / SMTP_PORT= / SMTP_USER= / SMTP_PASS= / REPORT_EMAIL=   # weekly report
ELASTICSEARCH_URL= / ELASTICSEARCH_INDEX=cti-alerts                 # event forwarding
```
