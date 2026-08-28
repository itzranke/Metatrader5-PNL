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
| 3 Database & Accounts (CRUD akun, quota 2/user, demo generator 60–90 hari <5 dtk, preset HF, halaman Akun web) | ✅ selesai |
| 4 MT5 Connector (pairing code 8 digit TTL 5 mnt, device auth Argon2+anti-replay, sync batch 500 idempoten, outbox offline, heartbeat) | ✅ selesai |
| 5 PnL Dashboard & Analytics (KPI cards, equity curve recharts, kalender P&L heatmap, posisi terbuka, trade terbaru + filter, agregasi multi-akun, packages/analytics murni) | ✅ selesai |
| 6 Jurnal Trading (CRUD jurnal per trade/manual, emosi 3 fase, confidence/discipline, 5 flag psikologi, tag many-to-many, screenshot upload 5 MB, filter tag/setup/bulan) | ✅ selesai |
| 7 Export CSV + Settings (trades.csv/journal.csv BOM UTF-8, profil, ganti password, sesi aktif + cabut) — **MVP 9 fitur LENGKAP** | ✅ selesai |
| 8–16 | lihat BLUEPRINT §34 |

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
