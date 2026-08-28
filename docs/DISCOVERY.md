# 🧭 STAGE 1 — DISCOVERY
## MT5 Trading Journal & Analytics Platform — Analisis Requirement

> Status: **sebelum blueprint final**. Dokumen ini berisi analisis kontradiksi,
> ambiguitas, requirement hilang, dependensi, dan risiko. Keputusan arsitektur
> kritis ditandai `[DECISION REQUIRED]` — sedang menunggu jawaban user.

---

## 1. Ringkasan

Requirement 35 fitur **realistis dan saling mendukung**, dengan 4 catatan besar:

1. Daftar 35 "fitur" mencampur **fitur asli, kemampuan teknis, dan standar kualitas** → perlu dinormalisasi (lihat §2.1).
2. Ada **2 keputusan besar yang mengubah seluruh arsitektur** → harus dijawab user dulu (stack & deployment).
3. Beberapa keputusan lama dari sesi sebelumnya **tertimpa** requirement baru (multi-account, backtest, prop sim, light mode kini resmi masuk scope).
4. Tidak ada kontradiksi fatal — semuanya bisa diakomodasi dengan phasing yang benar.

---

## 2. Analisis Requirement

### 2.1 Kontradiksi & masalah dalam daftar 35 fitur

| # | Masalah | Resolusi yang direkomendasikan |
|---|---|---|
| Fitur 1 vs 16 | "Akun Web Multi-User" dan "Model Web Multi-User" — **duplikat** | Gabung jadi satu: *Multi-User Web Platform* |
| Fitur 19 | "Siap Deploy ke Cloud" — bukan fitur, **standar kualitas** | Keluar dari feature tree; jadi acceptance criterion seluruh sistem |
| Fitur 17 | "Responsive + PWA" — dua hal berbeda | Pisah: *Responsive* (seluruh halaman) + *PWA* (installable, offline journal) |
| Fitur 4/10 | "Dashboard P&L" vs "Kalender P&L Bulanan" | Kalender P&L = sub-komponen Dashboard (bukan fitur terpisah) |
| Dua "kalender" | Kalender **P&L** (bulanan) vs Kalender **Ekonomi** (event news) | Nama dibedakan tegas: `P&L Calendar` vs `Economic Calendar` — dua modul berbeda |
| MD3 (keputusan lama) vs §18 baru | Material Design 3 vs "Trading terminal + SaaS analytics" | **Tidak bertabrakan**: MD3 tetap sebagai bahasa komponen (token, elevasi, motion), layout diadaptasi jadi dense trading terminal |
| V1-SCOPE council | Multi-account, backtest, prop sim, light mode sempat ditunda | **Requirement baru menang**: semua masuk scope resmi — tetap di fase akhir (Phase 11+) |
| Keputusan lama | "Trading order tidak diminta" (read-only) | Tetap berlaku: connector **read-only**. §8 prompt ("jangan simpan password MT5") konsisten dengan ini ✅ |
| Multi-account vs 1 connector | Berapa akun per desktop connector? | 1 connector = 1 user = **banyak akun MT5** (MT5 terminal punya banyak login). Akun dipilih/ditambahkan di UI; connector kirim semua akun yang user pilih |
| PWA offline vs real-time | Trade data butuh live, jurnal bisa offline | Sesuai §28 prompt: pisah offline-capable (jurnal, screenshot, cache baca) vs online-required (harga, sync, kalender ekonomi) ✅ |

### 2.2 Ambiguitas → `[DECISION REQUIRED]` (diminta ke user)

| ID | Keputusan | Opsi | Rekomendasi |
|---|---|---|---|
| **DR-01** | **Stack frontend + backend** | (a) React+Vite+TS + Python FastAPI (b) Flask + vanilla JS (pakai kode lama) (c) Next.js monorepo TS | **a** — lihat §4 |
| **DR-02** | **Deployment + hosting PostgreSQL** | (a) Render + Neon (b) VPS Docker (c) Railway/Fly | **a** — zero-ops, reuse render.yaml |
| **DR-03** | **Demo account: sintetis vs HF asli** | (a) dua mode (b) sintetis saja (c) HF asli saja | **a** — dua mode |
| **DR-04** | **Sumber data backtest** | (a) riwayat connector + CSV (b) API eksternal (c) sintetis dulu | **a** |
| DR-05 | Metode auth | email/password (lama) vs + Google OAuth | email/password + verifikasi email; OAuth opsional Phase 3 |
| DR-06 | Email provider | Resend / SendGrid / SMTP sendiri | Resend (free tier 3k/bln, API modern) |
| DR-07 | Penyimpanan screenshot | lokal disk vs S3-compatible (R2/S3) | lokal dulu (fase 1) → R2 saat cloud (fase 2) |
| DR-08 | Sumber kalender ekonomi | scraping Forex Factory (gratis, rapuh) / API berbayar / manual import | **adapter pattern** + manual import; API berbayar opsional — jangan jadi dependency kritis |
| DR-09 | Market data watchlist/chart | via connector saja vs + API eksternal | connector dulu (data akun konsisten); eksternal opsional |
| DR-10 | Prop firm rules | preset (FTMO/5ers/FundedNext) + custom | preset + custom editor |
| DR-11 | Bahasa UI | Indonesia / Inggris | Indonesia (istilah trading tetap EN: BUY/SELL/swap…) |
| DR-12 | Mata uang multi-account | USD/EUR/IDR bercampur | tampilkan sesuai mata uang akun + konversi tampilan opsional (rate harian disimpan) |
| DR-13 | User deletion | hard delete vs soft delete | soft delete + anonymize (GDPR-lite) |
| DR-14 | PDF generation | weasyprint / wkhtmltopdf / headless chrome | weasyprint (Python-native, di worker) |
| DR-15 | Push notifikasi PWA | Web Push (FCM/VAPID) vs Telegram saja | Telegram + email dulu; Web Push fase akhir (iOS tidak konsisten) |

### 2.3 Requirement yang HILANG (tidak ada di daftar 35)

| Yang hilang | Kenapa penting | Solusi |
|---|---|---|
| **Password reset** | Ada di feature tree auth tapi tidak ada di daftar | Wajib ada sejak Phase 2 (butuh email provider → DR-06) |
| **Rate limiting & quota per user** | Multi-user publik = abuse risk | Per-user rate limit di API gateway layer |
| **Audit log** (sudah ada di daftar tabel ✅) | Compliance & debugging | Log semua mutasi sensitif |
| **Migrasi data dari model lama** | Ada backup SQLite | User bilang "ulang dari awal" → **skip**; cukup tool import CSV |
| **Halaman /login, /register** | Ada di page tree prompt | Termasuk Phase 2 |
| **Status/harga diri connector** | Debug sync | Endpoint `/api/connector/status` + halaman status di Settings |
| **Timezone akun MT5** | Broker timezone + DST | Simpan `timezone` per trading account; semua timestamp UTC + offset broker |
| **Currency conversion** | Lihat DR-12 | Rate harian disimpan di `currency_rates` |

### 2.4 Risiko teknis & keamanan (peringkat)

| Risiko | Level | Mitigasi |
|---|---|---|
| Scraping kalender ekonomi (ToS/rapuh) | 🔴 HIGH | Adapter + manual import; bukan dependency kritis |
| Distribusi connector (user non-teknis) | 🔴 HIGH | PyInstaller exe + auto-update via GitHub Releases + checksum |
| Backtest correctness (lookahead bias) | 🔴 HIGH | Engine sandbox, data point-only, validasi spread/slippage, dokumentasi batas |
| Salah mapping akun MT5 → user | 🟠 MED | Pairing token sekali pakai + konfirmasi login/server di UI + server validasi |
| Upload screenshot (malware/EXIF) | 🟠 MED | Validasi MIME magic bytes, resize, strip EXIF, limit 5MB, virus scan opsional |
| Multi-currency aggregation (analytics lintas akun) | 🟠 MED | Konversi ke mata uang dasar user; tandai estimasi |
| DST/broker timezone (pelajaran dari bug lama: `datetime`/`digits`) | 🟠 MED | Timestamp UTC ketat + offset broker disimpan; unit test timezone |
| Webhook connector → server (spoofing) | 🟠 MED | HMAC-SHA256 signing + API key per device |
| DB failure / data hilang | 🟠 MED | Managed Postgres (backup otomatis) + export CSV |
| PWA push di iOS | 🟡 LOW | Telegram sebagai kanal utama; Web Push fallback |

---

## 3. Dependensi fitur (inti, untuk phasing)

```
Auth ──► User ──► Trading Account (multi) ──► MT5 Connection
                              │                    │
                              ▼                    ▼
                     Journal (manual)        Trades/Deals (sync)
                              │                    │
                              ▼                    ▼
                    Psychology Entries      Analytics Engine
                                                    │
                          ┌───────────────┬─────────┼──────────┬──────────────┐
                          ▼               ▼         ▼          ▼              ▼
                   Performance Score  MAE/MFE   Insights   Reports      Watchlist/Charts
                          │               │         │          │              │
                          ▼               ▼         ▼          ▼              ▼
                   Goals/Prop Sim     Backtest  Notifications  Export      Market Data
```

**Aturan phasing:** tidak ada modul yang bisa dibangun sebelum parent-nya.
Backtest butuh → Trades + Candle data. Prop sim butuh → Analytics + Trades.
Reports butuh → Analytics + Journal. Insight butuh → Analytics + Journal + Psychology.

---

## 4. Rekomendasi stack (ringkas — detail lengkap di blueprint)

| Lapisan | Rekomendasi | Alasan |
|---|---|---|
| Backend | **Python + FastAPI** | Library `MetaTrader5`/`mtapi` hanya tersedia di Python; logika `journal_math.py` lama bisa di-reuse; FastAPI = async + OpenAPI docs otomatis (REST API lengkap gratis) |
| Frontend | **React 19 + Vite + TypeScript + Tailwind** | 35 fitur = UI kompleks (replay, backtest, insight grid); TS mencegah regresi; MD3 via komponen sendiri (bukan MUI) agar sesuai "trading terminal" |
| Charts | **lightweight-charts** (sudah teruji) + Recharts untuk statis | Live chart & equity curve |
| DB | **PostgreSQL 16** (Neon managed) + SQLAlchemy 2 + Alembic | Requirement eksplisit; migration versioned |
| Cache/Queue | Redis (Rate limit, job queue via RQ/Celery) | Sederhana, cukup |
| Connector | **Python + PyInstaller** (desktop), MetaTrader5 lib, REST+HMAC | Reuse pola connector lama |
| PWA | Workbox + manifest + Web Push (akhir) | Offline journal queue |
| Deploy | Render (web+worker) + Neon PG + Cloudflare R2 (screenshot) | Reuse render.yaml |
| Worker | Python (RQ) — sync processing, analytics recalc, reports, export, notifikasi | Pisah dari API |

---

## 5. Kesimpulan Stage 1

- **Siap blueprint setelah 4 pertanyaan kunci dijawab** (DR-01…DR-04 — diajukan via UI pertanyaan).
- DR-05…DR-15 sudah ada rekomendasi — akan dipakai sebagai **default** di blueprint, tetap ditandai `[DECISION REQUIRED]` agar developer penerima tahu ini keputusan terbuka.
- Fase berikutnya: **STAGE 2 (Arsitektur)** → **STAGE 3 (Development Blueprint)** → satu dokumen `BLUEPRINT.md` 41 bagian.
