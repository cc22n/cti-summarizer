# CTI Summarizer + Trend Predictor

[![CI](https://github.com/cc22n/cti-summarizer/actions/workflows/ci.yml/badge.svg)](https://github.com/cc22n/cti-summarizer/actions/workflows/ci.yml)
[![E2E](https://github.com/cc22n/cti-summarizer/actions/workflows/e2e.yml/badge.svg)](https://github.com/cc22n/cti-summarizer/actions/workflows/e2e.yml)
[![Lint](https://github.com/cc22n/cti-summarizer/actions/workflows/lint.yml/badge.svg)](https://github.com/cc22n/cti-summarizer/actions/workflows/lint.yml)

Plataforma de inteligencia de amenazas (CTI) que ingesta feeds publicos de ciberseguridad, genera resumenes ejecutivos con un LLM y predice tendencias de amenazas con modelos de series temporales.

---

## Que hace este proyecto

El problema que resuelve: los equipos de seguridad reciben cientos de alertas diarias de fuentes distintas (NVD, CISA, OTX, MITRE, blogs) en formatos incompatibles. Leerlas manualmente es inviable.

Esta plataforma:
1. **Ingesta** automaticamente 5 fuentes CTI publicas en un formato unificado
2. **Normaliza** cada alerta con severidad consistente (critica / alta / media / baja / info)
3. **Resume** alertas individuales y genera un digest diario usando Grok 4.1 Fast (xAI)
4. **Predice** el volumen de amenazas para los proximos 14 dias con Prophet (ML)
5. **Visualiza** todo en un dashboard React con graficos, filtros y detalle por alerta

---

## Estado del proyecto

| Fase | Descripcion | Estado |
|------|-------------|--------|
| Fase 1 | Ingestion + Normalizacion (NVD + CISA KEV) + FastAPI + Tests | Completa |
| Fase 2 | Adaptadores OTX + MITRE ATT&CK + RSS + Summarizacion con Grok | Completa |
| Fase 3 | Dashboard React SPA (Vite + TypeScript + Recharts) | Completa |
| Fase 4 | Prediccion de tendencias con Prophet (forecast 14 dias) | Completa |
| Fase 5 | Mejoras de seguridad, rendimiento y calidad | Completa |

---

## Como funciona (arquitectura)

```
Fuentes externas          Pipeline backend              Frontend
-----------------         ------------------            --------
NVD (NIST)      ─┐
CISA KEV        ─┤─> Adaptadores ─> Orquestador ─> raw_alerts
AlienVault OTX  ─┤              │              └─> normalized_alerts
MITRE ATT&CK    ─┤              │                         │
RSS blogs       ─┘              │                         ▼
                                │              Summarization Service
                                │               (Grok 4.1 Fast / xAI)
                                │                         │
                                │              Prediction Service
                                │               (Prophet ML)
                                │                         │
                                └──────────> FastAPI REST API
                                                          │
                                             React SPA Dashboard
                                              (Vite + TanStack Query)
```

### Flujo de ingestion paso a paso

```
1. Celery Beat dispara la tarea segun el schedule (cron)
2. La tarea llama a IngestionOrchestrator.run(adapter)
3. El adaptador obtiene alertas de la fuente externa via HTTP
4. El orquestador deduplica por (source_id, external_id) con un bulk SET lookup
5. Guarda las nuevas alertas como RawAlert (JSON crudo en JSONB)
6. NormalizationService transforma cada RawAlert en NormalizedAlert
7. Se actualizan source.last_polled_at e IngestionLog
8. El commit final persiste todo en una sola transaccion
```

### Normalizacion de severidad por fuente

| Fuente | Logica de severidad |
|--------|---------------------|
| NVD | CVSS score: >=9.0 critica, >=7.0 alta, >=4.0 media, >0 baja |
| CISA KEV | Campana ransomware = critica, resto = alta |
| OTX | indicators >= 50 alta, >= 10 media, resto baja; tag ransomware = critica |
| MITRE ATT&CK | Siempre info (tecnicas de referencia, no amenazas activas) |
| RSS | Siempre info |

### Summarizacion LLM

- `SummarizationService` usa el SDK de OpenAI apuntando a la API de xAI (compatible)
- Dos tipos de summary: `alert` (por alerta) y `digest` (batch de 24h)
- Si no hay `XAI_API_KEY` configurada, el servicio retorna `None` sin fallar
- Los summaries se guardan en la tabla `summaries` y se exponen via REST

### Prediccion con Prophet

- Entrena sobre 90 dias de datos historicos de `normalized_alerts`
- Genera forecast de 14 dias para 6 series: `critical`, `high`, `medium`, `low`, `info`, `total`
- Cuando una serie tiene menos de 10 dias con datos (sparse), usa media movil de 7 dias como fallback
- Los resultados se almacenan en `trend_predictions` con `(run_id, series_key, target_date)` unico
- Prophet se importa dentro de la funcion (`deferred import`) para que el backend arranque aunque Prophet no este instalado

---

## Stack tecnologico

| Capa | Tecnologia |
|------|------------|
| Backend API | FastAPI (Python 3.11+) |
| Base de datos | PostgreSQL con psycopg v3 |
| ORM | SQLAlchemy 2.x (mapped_column) |
| Migraciones | Alembic |
| Cola de tareas | Celery + Redis |
| Cache | Redis |
| LLM | Grok 4.1 Fast (xAI) via SDK OpenAI-compatible |
| ML | Prophet 1.1.6 con fallback rolling average |
| Frontend | React 19 + Vite 8 + TypeScript 5.9 |
| Graficos | Recharts 3 |
| Data fetching | TanStack Query v5 |
| Estilos | Tailwind CSS v4 |
| Tests | pytest + httpx (SQLite en memoria) |

---

## Requisitos previos

- Python 3.11+
- Node.js 20+
- PostgreSQL corriendo localmente
- Redis corriendo localmente
- (Opcional) Claves de API: NVD, OTX, xAI

---

## Ejecucion del proyecto

### 1. Instalar dependencias Python

```powershell
pip install -r requirements.txt --break-system-packages
```

### 2. Configurar variables de entorno

```powershell
copy .env.example .env
```

Editar `.env` con tus claves:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cti_summarizer
REDIS_URL=redis://localhost:6379/0

NVD_API_KEY=tu_clave_nvd          # gratis en nvd.nist.gov
OTX_API_KEY=tu_clave_otx          # gratis en otx.alienvault.com
XAI_API_KEY=tu_clave_xai          # requerida para summaries LLM

API_KEY=clave_secreta_opcional    # protege los endpoints POST (dejar vacio en dev)
CORS_ORIGINS=http://localhost:5173
```

### 3. Crear la base de datos y aplicar migraciones

```powershell
python -m scripts.setup_db
```

Este script:
- Crea la DB si no existe
- Crea las 8 tablas
- Aplica las migraciones Alembic (incluyendo indices de rendimiento)
- Inserta las 8 fuentes CTI predefinidas

### 4. Iniciar el backend API

```powershell
# Terminal 1
uvicorn app.main:app --reload
```

API disponible en: `http://localhost:8000`
Documentacion interactiva: `http://localhost:8000/docs`

### 5. Iniciar el frontend

```powershell
# Terminal 2
cd frontend
npm install
npm run dev
```

Dashboard disponible en: `http://localhost:5173`

### 6. Iniciar el worker de Celery

```powershell
# Terminal 3
celery -A app.celery_app worker --loglevel=info
```

Procesa las tareas de ingestion, summarizacion y prediccion en segundo plano.

### 7. Iniciar el scheduler de Celery Beat

```powershell
# Terminal 4
celery -A app.celery_app beat --loglevel=info
```

Dispara las tareas segun el schedule automaticamente.

### 8. (Opcional) Ingestion manual inmediata

```powershell
python -m scripts.run_ingestion --all
```

### 9. Ejecutar los tests

```powershell
pytest -v --tb=short

# Con cobertura
pytest --cov=app --cov-report=html
```

---

## Schedule de tareas automaticas

| Tarea | Frecuencia | Horario |
|-------|------------|---------|
| Ingesta NVD | Cada 6h | 00:00, 06:00, 12:00, 18:00 |
| Ingesta CISA KEV | Diario | 07:00 |
| Ingesta OTX | Cada 6h | 01:30, 07:30, 13:30, 19:30 |
| Ingesta MITRE ATT&CK | Semanal | Lunes 02:00 |
| Ingesta RSS | Cada 2h | Cada hora par |
| Digest diario (LLM) | Diario | 08:00 |
| Prediccion de tendencias | Semanal | Lunes 03:00 |

---

## Endpoints REST

### Generales

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/health` | Estado del servicio |

### Alertas

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/alerts` | Lista paginada con filtros por severidad, fuente y busqueda |
| GET | `/api/v1/alerts/{id}` | Detalle de una alerta |
| GET | `/api/v1/alerts/stats` | Estadisticas agregadas |

### Fuentes

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/sources` | Lista todas las fuentes CTI |
| GET | `/api/v1/sources/{id}/health` | Metricas de salud de una fuente |
| POST | `/api/v1/sources/{id}/poll` | Fuerza ingestion inmediata via Celery |

### Dashboard

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/dashboard/overview` | Metricas globales (1 query consolidada) |
| GET | `/api/v1/dashboard/timeline` | Timeline de alertas por dia (7-90 dias) |

### Summaries (LLM)

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/summaries` | Lista summaries con paginacion |
| GET | `/api/v1/summaries/{id}` | Detalle de un summary |
| GET | `/api/v1/summaries/digest/latest` | Ultimo digest diario generado |
| POST | `/api/v1/summaries/generate` | Genera summary por IDs de alerta |
| POST | `/api/v1/summaries/digest/generate` | Genera digest de las ultimas N horas |

### Predicciones (ML)

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/predictions/latest` | Ultimo forecast con todas las series |
| POST | `/api/v1/predictions/generate` | Dispara nueva generacion via Celery |

Los endpoints POST requieren el header `X-API-Key` si `API_KEY` esta configurada en `.env`.

---

## Esquema de base de datos

```
sources               raw_alerts              normalized_alerts
--------              ----------              -----------------
id                    id                      id
name                  source_id (FK)          raw_alert_id (FK)
source_type           external_id             title
base_url              raw_data (JSONB)        description
is_active             is_processed            severity
last_polled_at        ingested_at             cvss_score
                                              source_name
ingestion_logs                                attack_vectors (JSONB)
--------------        alert_categories        mitre_techniques (JSONB)
id                    ----------------        iocs (JSONB)
source_id (FK)        id                      published_date
status                name                    normalized_at
alerts_fetched        description
alerts_new            keywords (JSONB)        summaries
error_message                                 --------
started_at            alert_category_map      id
completed_at          ------------------      normalized_alert_id (FK)
                      alert_id (FK)           summary_type
trend_predictions     category_id (FK)        content
-----------------                             model_used
id                                            created_at
run_id
series_key
target_date
predicted_count
lower_bound
upper_bound
generated_at
```

---

## Estructura del proyecto

```
cti-summarizer/
├── app/
│   ├── main.py                          # FastAPI entry point, CORS
│   ├── config.py                        # Settings via pydantic-settings
│   ├── database.py                      # Engine, sesiones, Base
│   ├── celery_app.py                    # Configuracion Celery
│   ├── dependencies.py                  # require_api_key dependency
│   ├── models/                          # SQLAlchemy ORM models
│   ├── schemas/                         # Pydantic response schemas
│   ├── api/v1/                          # Routers FastAPI
│   ├── services/
│   │   ├── ingestion/                   # Un adaptador por fuente CTI
│   │   ├── ingestion_orchestrator.py    # Pipeline completo
│   │   ├── normalization.py             # Mapeado a NormalizedAlert
│   │   ├── summarization_service.py     # Cliente Grok LLM
│   │   └── prediction_service.py        # Prophet + fallback
│   └── workers/
│       ├── ingestion_tasks.py           # Tareas Celery + Beat schedule
│       ├── summary_tasks.py             # Tareas de summarizacion
│       ├── prediction_tasks.py          # Tarea de prediccion
│       └── utils.py                     # run_async compartido
├── frontend/
│   └── src/
│       ├── types/                       # Tipos TypeScript
│       ├── services/                    # Clientes axios por dominio
│       ├── hooks/                       # TanStack Query hooks
│       ├── components/                  # Componentes reutilizables
│       └── pages/                       # Paginas de la SPA
├── alembic/versions/                    # Migraciones de DB
├── tests/                               # pytest con SQLite en memoria
├── scripts/
│   ├── setup_db.py                      # Init DB + seed fuentes
│   └── run_ingestion.py                 # Ingestion manual
├── .env.example
└── requirements.txt
```

---

## Decisiones de diseno relevantes

- **psycopg v3** (no psycopg2): evita bug de encoding en Windows con `postgresql+psycopg://`
- **Adaptador pattern**: cada fuente CTI es una clase independiente que hereda `BaseAdapter`
- **Raw + Normalized**: almacenamiento en dos etapas preserva el JSON original y permite re-normalizacion
- **SQLite para tests**: rapido, sin dependencias externas, creado/destruido por fixture
- **Deferred import de Prophet**: `from prophet import Prophet` dentro de la funcion — el backend arranca aunque Prophet no este instalado
- **`/digest/latest` antes de `/{id}`**: orden de declaracion en FastAPI evita que "digest" se interprete como entero
- **Bulk deduplication**: carga todos los `external_id` existentes en un `set` antes del loop — evita N queries individuales

---

## Licencia

MIT
