# MT5 Trading Journal & Analytics Platform

Web multi-user untuk jurnal trading MT5: sinkronisasi akun MetaTrader 5 via Desktop
Connector, jurnal manual, analisis performa, insight, psikologi, laporan, simulasi
prop firm & backtest.

> Blueprint lengkap: lihat `docs/` (BLUEPRINT.md, KEPUTUSAN-FINAL.md, DISCOVERY.md, RISET.md)
> di workspace root project induk. Aturan kerja: `AGENTS.md` (ponytail + council).

## Status fase

| Fase | Status |
|---|---|
| 0–1 Foundation (repo, config, DB, healthz, web skeleton) | ✅ selesai |
| 2 Authentication (register/verify/login/refresh/logout/forgot/reset, session mgmt, rate limit, halaman auth web) | ✅ selesai |
| 3 Database & Accounts | ⏳ berikutnya |
| 4–16 | lihat BLUEPRINT §34 |

## Struktur

```
apps/
  web/        React 19 + Vite + TS + Tailwind (PWA base)
  api/        FastAPI (REST /api/v1)
  worker/     RQ worker (fase berikutnya)
  connector/  Desktop connector MT5 (fase 4)
packages/
  config/     env schema (pydantic-settings)
  db/         SQLAlchemy 2 models + Alembic
  analytics/  pure math (fase 7)
infra/        docker-compose.dev.yml
```

## Quickstart (dev)

```bash
# 1. Infra lokal (PostgreSQL + Redis)
docker compose -f infra/docker-compose.dev.yml up -d

# 2. Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

# 3. Migrasi DB
alembic upgrade head

# 4. API
uvicorn apps.api.app.main:app --reload --port 8000   # docs di /docs

# 5. Web
cd apps/web && npm install && npm run dev            # http://localhost:5173
```

## Test & lint

```bash
pytest -q          # backend (sqlite untuk CI/dev test)
ruff check .       # lint python
cd apps/web && npm test && npm run build
```

## Keputusan terkunci

Stack: React 19 + FastAPI + PostgreSQL 16 + Redis + RQ · Deploy: Render + Neon.
Register lengkap: `KEPUTUSAN-FINAL.md` di workspace induk.
