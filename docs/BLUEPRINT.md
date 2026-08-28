# 📐 MASTER SYSTEM BLUEPRINT
## MT5 Trading Journal & Analytics Platform

**Versi:** 1.0 (final) · **Tanggal:** 2026-08-29 · **Status:** siap development
**Keputusan user:** React+FastAPI · Render+Neon · demo dua mode · backtest data connector+CSV
**Dokumen pendukung:** `RISET.md` (riset) · `DISCOVERY.md` (stage 1) · `ui-foundation/` (tokens) · `AGENTS.md` (aturan kerja)

---

# 1. EXECUTIVE SUMMARY

Platform web **multi-user** untuk jurnal trading MT5: sinkronisasi akun MetaTrader 5
via **Desktop Connector**, jurnal manual, analisis performa, insight, psikologi,
laporan, hingga simulasi prop firm & backtest. **Tidak melakukan eksekusi order**
(connector read-only).

**Arsitektur inti:**

```
Browser (React PWA)  ──►  API (FastAPI)  ──►  PostgreSQL (Neon)
       ▲                       │  ▲
       │                       ▼  │ (HMAC + API key)
       │                  Redis + Worker (RQ)
       │                       │
       └── MT5 Desktop Connector (Python, PyInstaller) ──► MT5 Terminal
```

**Stack:** React 19 + Vite + TS + Tailwind · Python FastAPI · PostgreSQL 16 · Redis · RQ ·
lightweight-charts · PyInstaller connector · Render + Neon · PWA (Workbox).

**Phasing:** MVP (alur inti + jurnal + analytics dasar) → Phase 2 (multi-account
penuh, MAE/MFE, kalender ekonomi, laporan) → Phase 3 (score, insight, prop firm,
backtest/replay, notifikasi, PWA penuh) → Advanced (Web Push, OAuth, PostgreSQL RLS penuh).

**Keputusan terbuka (default dipakai, lihat §40):** DR-05…DR-15 di DISCOVERY.md.
Dokumen ini **menggantikan** `V1-SCOPE.md` (hasil council) — requirement 35 fitur
resmi lebih baru dan menang.

---

# 2. PRODUCT DEFINITION

| Aspek | Definisi |
|---|---|
| **Nama** | MT5 Trading Journal & Analytics Platform |
| **Pengguna** | Trader MT5 (retail, prop firm trainee) — non-teknis |
| **Nilai utama** | 1) PnL & performa selalu terlihat, 2) jurnal konteks per trade (notes, setup, emosi, tag), 3) insight & laporan otomatis, 4) aman & multi-device (web) |
| **Bukan** | Bukan platform eksekusi order; bukan broker; bukan signal service |
| **Model** | Web multi-user + Desktop Connector (Auto-Sync). Bisa dipakai dari PC, Android, iOS via browser (responsive + PWA) |
| **Mata uang** | Mengikuti mata uang akun MT5 (USD/EUR/IDR…); konversi tampilan opsional |
| **Bahasa UI** | Indonesia (istilah trading tetap EN) |
| **Komersial** | Free tier + quota; monetisasi bukan scope v1 |

**Persona:**
- **Andi (pemula):** baru kenal MT5 → mode "Data Contoh" untuk eksplorasi tanpa risiko.
- **Budi (aktif):** trader harian, butuh sync otomatis + jurnal cepat + insight.
- **Citra (prop firm):** butuh simulasi rules prop firm + laporan mingguan.

---

# 3. FEATURE TREE

> Normalisasi dari 35 fitur → 7 modul + 27 fitur. Kolom per node:
> **F**=fungsi · **I**=input · **O**=output · **D**=dependency · **Data**=entity ·
> **R**=role · **A**=API · **U**=komponen UI

```
MT5 JOURNAL
├── A. Authentication & User
│   ├── A1 Register            [F] buat akun; [I] username, email, password; [O] akun+verifikasi email
│   │     [D] email provider; [Data] users; [R] public; [A] POST /auth/register; [U] form register
│   ├── A2 Login / Logout      [F] sesi aman; [I] kredensial; [O] JWT+refresh cookie
│   │     [D] users, sessions; [R] public; [A] POST /auth/login, /auth/logout; [U] form login
│   ├── A3 Forgot/Reset Password  [I] email → token sekali pakai (15 mnt); [A] POST /auth/forgot, /auth/reset
│   ├── A4 Email Verification  [I] token 24 jam; [A] POST /auth/verify
│   ├── A5 Session & Device    [I] daftar sesi aktif; [O] revoke sesi/device; [Data] sessions, devices
│   │     [A] GET/DELETE /auth/sessions/:id; [U] daftar sesi + tombol revoke
│   └── A6 2FA (Phase 3)       TOTP; [A] POST /auth/2fa/*
│
├── B. Trading Accounts (multi-account per user)
│   ├── B1 Daftar Akun         [F] kelola akun MT5; [I] nama, broker, login, server, tipe; [O] kartu akun
│   │     [D] auth; [Data] trading_accounts; [A] GET/POST/PATCH/DELETE /accounts; [U] halaman accounts
│   ├── B2 Akun Demo Sintetis  [F] buat "Data Contoh"; [I] 1 klik; [O] akun demo + trades sintetis
│   │     [D] generator sintetis; [Data] trading_accounts(kind=demo) + trades; [A] POST /accounts/demo
│   ├── B3 Isi Akun Demo HF    [F] tombol isi login+server HF Markets; [O] kredensial terisi (password diisi user)
│   │     [D] preset HF; [A] GET /meta/broker-presets; [U] tombol #btnFillDemoAcc
│   ├── B4 Pilih Akun Aktif     [F] account selector global; [U] dropdown di topbar (persist di localStorage)
│   └── B5 Status Koneksi      [F] badge connector; [Data] mt5_connections; [A] GET /accounts/:id/connection
│
├── C. MT5 Connector & Sync
│   ├── C1 Pairing Device      [F] hubungkan connector; [I] pairing code 8 digit (5 mnt); [O] device terdaftar
│   │     [Data] connector_devices, mt5_connections; [A] POST /connector/pair, /connector/devices
│   ├── C2 Auto-Sync           [F] sync berkala + realtime posisi; [I] heartbeat, deal feed; [O] trades masuk DB
│   │     [Data] trades, deals, positions; [A] POST /connector/sync (HMAC); [U] toast "tersinkron"
│   ├── C3 Histori & Inkremen  [F] import riwayat + delta sejak ticket terakhir; [D] C2
│   ├── C4 Reconnect/Offline   [F] antrian lokal + backoff; [Data] connector_devices.state
│   └── C5 Status & Diagnostik [F] halaman status koneksi; [A] GET /connector/status; [U] halaman settings > connector
│
├── D. Trading Data
│   ├── D1 Open Positions      [F] posisi terbuka real-time; [I] deals sync; [O] tabel + PnL float
│   │     [Data] positions; [A] GET /positions; [U] tabel posisi + refresh interval
│   ├── D2 Closed Positions    [F] riwayat tertutup; [Data] trades; [A] GET /trades?status=closed
│   ├── D3 Trade History       [F] semua transaksi + deal; [Data] trades, deals; [A] GET /trades, /deals
│   ├── D4 Detail Trade        [F] drawer/modal detail: entry/exit, swap, komisi, MAE/MFE, jurnal terkait
│   │     [Data] trades+journal_entries; [A] GET /trades/:id; [U] modal detail
│   ├── D5 Manual Trade Entry  [F] catat trade manual (tanpa MT5); [I] simbol, arah, harga, lot, waktu;
│   │     [O] trade tersimpan; [A] POST /trades (kind=manual); [U] modal + screenshot upload
│   └── D6 Watchlist & Quotes  [F] pantau harga simbol; [I] simbol pilihan; [O] quote live (via connector);
│   │     [Data] watchlists, symbol_prices; [A] GET/POST /watchlist, GET /quotes; [U] sidebar watchlist
│
├── E. Journal & Psychology
│   ├── E1 Jurnal per Trade    [F] notes, setup, emosi, tag, screenshot; [I] form jurnal; [O] entri tersimpan
│   │     [Data] journal_entries, trade_tags, trade_notes, trade_screenshots; [A] POST/PATCH /trades/:id/journal
│   ├── E2 Tracker Psikologi   [F] emosi before/during/after + confidence + rule adherence;
│   │     [Data] psychology_entries; [A] GET/POST /psychology
│   ├── E3 Korelasi Psikologi↔Hasil  [F] avg R by tag + signifikansi; [D] E1+E2+analytics
│   └── E4 Kalender Jurnal     [F] heatmap entri jurnal per hari; [Data] journal_entries; [U] kalender
│
├── F. Analytics & Insights
│   ├── F1 Dashboard P&L       [F] KPI + equity curve + kalender P&L bulanan; [I] rentang tanggal, filter
│   │     [D] D3; [Data] daily_statistics, equity_snapshots; [A] GET /analytics/dashboard; [U] stat cards, chart
│   ├── F2 Metrik 12+          [F] 21 metrik (lihat §13); [A] GET /analytics/performance
│   ├── F3 Filter Analisis     [F] filter simbol/arah/tag/setup/rentang/sesi; [A] ?filters= pada endpoint analitik
│   ├── F4 Performance Score   [F] skor 0–100; [D] F2; [A] GET /analytics/score
│   ├── F5 MAE/MFE             [F] analisis ekskursi; [D] data harga path; [A] GET /analytics/mae-mfe
│   ├── F6 Insight Engine      [F] pola tersembunyi tervalidasi; [D] F2+E; [A] GET /insights
│   ├── F7 Laporan Mingguan/Bulanan  [F] laporan PDF/email; [D] F2+F6; [A] GET/POST /reports
│   └── F8 Kalender Ekonomi    [F] event news; [Data] economic_events; [A] GET /economic-calendar
│
├── G. Simulasi & Lanjutan
│   ├── G1 Prop Firm Simulator [F] status pass/fail vs rules; [Data] prop_firm_*; [A] GET/POST /prop-firm
│   ├── G2 Backtesting         [F] uji strategi rule-based; [Data] backtests, backtest_trades; [A] POST /backtests
│   ├── G3 Trade Replay        [F] putar ulang candle; [Data] candles + trade_replays; [A] POST /replays
│   └── G4 Deposit/Withdrawal  [F] lacak dana; [Data] deposits, withdrawals; [A] GET/POST /transactions
│
├── H. Reports & Export & Notifications
│   ├── H1 Export CSV/Excel/PDF  [F] async export; [A] POST /exports; [U] tombol + status job
│   ├── H2 Notifikasi Telegram/Email  [F] trigger + preferensi; [Data] notifications*; [A] GET/POST /notifications
│   ├── H3 Goal Tracking       [F] target harian/bulanan; [Data] goals; [A] GET/POST /goals
│   └── H4 Laporan Terjadwal   [F] cron mingguan/bulanan; [D] worker
│
├── I. Admin & System
│   ├── I1 Admin Panel         [F] kelola user, quota, fitur; [Data] users, audit_logs; [A] /admin/*
│   ├── I2 Audit Log           [F] jejak mutasi sensitif; [Data] audit_logs
│   └── I3 Health & Metrics    [F] /healthz, /metrics; [Data] —; [A] public GET /healthz
```

**Per-node penjelasan lengkap (contoh 3 node penting):**

**D2 Closed Positions**
F: menampilkan posisi yang sudah ditutup + hasil bersih (P/L + swap + komisi).
I: filter (rentang, simbol, arah, tag). O: tabel + total agregat.
D: D1 (data deal), F2 (agregasi). Data: `trades` (status=closed), `deals`, `trade_tags`.
R: pemilik akun. A: `GET /api/v1/trades?status=closed&from&to&symbol`.
Entity: `trades` (ticket, account_id, symbol, side, volume, open_price, close_price, open_time, close_time, net_profit, swap, commission, mae, mfe). UI: tabel dense + filter bar + summary strip.

**E1 Jurnal per Trade**
F: mencatat konteks trade (kenapa masuk, setup, emosi, tag, screenshot, pelajaran).
I: form jurnal (5 field inti: setup, emosi, confidence, notes, tags). O: entri jurnal + screenshot.
D: D4 (trade harus ada dulu; atau mode "trade manual + jurnal sekaligus").
Data: `journal_entries`, `trade_tags`, `trade_notes`, `trade_screenshots`.
R: pemilik trade. A: `POST/PATCH /api/v1/trades/{id}/journal` · `GET /api/v1/journal`.
Entity: `journal_entries` (1:1 trade opsional), tags many-to-many. UI: modal jurnal + tag chips + upload screenshot.

**F2 Metrik 12+**
F: menghitung 21 metrik dari trades tertutup dalam rentang/filter.
I: rentang, filter, akun. O: objek metrik + breakdown per simbol/hari/sesi.
D: D3, E (tag filter). Data: `trades`, `daily_statistics` (cache).
R: pemilik akun. A: `GET /api/v1/analytics/performance`.
Entity: dibaca dari `trades`; hasil disimpan di `analytics_snapshots` (cache).
UI: kartu KPI + tabel breakdown + chart distribusi.

> Node lainnya mengikuti pola yang sama; detail data/API lengkap ada di §9, §20.

---

# 4. SYSTEM ARCHITECTURE

```
┌─────────────────────────── Browser (React PWA) ───────────────────────────┐
│  React 19 + Vite + TS + Tailwind · lightweight-charts · Workbox SW       │
│  Pages: public/auth/app · offline: jurnal queue (IndexedDB)              │
└───────────────▲───────────────────────────────────┬──────────────────────┘
                │ HTTPS                             │ REST /api/v1 (JSON)
┌───────────────┴───────────────────────────────────▼──────────────────────┐
│                       API Server (FastAPI, Uvicorn)                      │
│  Auth (JWT+refresh cookie) · RBAC · Rate limit (Redis) · Validasi        │
│  Service layer: accounts · trades · journal · analytics · insight ·      │
│  reports · notifications · prop-firm · backtest · export · demo-gen      │
└───────────────┬──────────────────────────┬───────────────────────────────┘
                │ SQLAlchemy 2             │ enqueue jobs
┌───────────────▼───────────┐   ┌──────────▼──────────────┐
│ PostgreSQL 16 (Neon)      │   │ Redis + RQ Workers      │
│ · Alembic migrations      │   │ · sync processing       │
│ · multi-tenant (user_id)  │   │ · analytics recalc      │
│ · snapshots & statistik   │   │ · reports/export/notif  │
└───────────────┬───────────┘   └──────────┬──────────────┘
                │                          │
        ┌───────▼──────────────────────────▼───────┐
        │ External: Resend (email) · Telegram API │
        │ Cloudflare R2 (screenshot, Phase 2)     │
        │ Sentry (error) · UptimeRobot            │
        └─────────────────────────────────────────┘

┌─────────────── MT5 Desktop Connector (Python + PyInstaller) ─────────────┐
│  MetaTrader5 lib (read-only) · polling MT5 terminal                      │
│  Pairing (code 8 digit) → HMAC-signed REST → API server                  │
│  Heartbeat 30s · sync inkremental · offline queue · auto-update          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Prinsip arsitektur:**
1. **API-first** — semua fitur via REST; frontend tidak pernah akses DB.
2. **Stateless API** — sesi di JWT/refresh cookie; state berat di Postgres/Redis.
3. **Worker memisahkan** semua kerja berat (sync bulk, recalc, report, export) dari request path.
4. **Tenant-aware** — `user_id` di setiap tabel + scoping di service layer (defense in depth: RLS optional).
5. **Idempoten sync** — unique constraint (account_id, ticket) mencegah duplikat.
6. **Observable** — health endpoint, structured logs, Sentry, audit log.

---

# 5. INFORMATION ARCHITECTURE

```
Level 1: App Shell (sidebar + topbar) — selalu ada di area login
├── 1. Dashboard          (default landing)
├── 2. Trading
│   ├── 2.1 Posisi Terbuka
│   ├── 2.2 Riwayat Trade
│   └── 2.3 Trade Baru (manual)
├── 3. Jurnal
│   ├── 3.1 Jurnal per Trade
│   ├── 3.2 Psikologi
│   └── 3.3 Kalender Jurnal
├── 4. Analitik
│   ├── 4.1 Performa (21 metrik)
│   ├── 4.2 MAE/MFE
│   ├── 4.3 Performance Score
│   └── 4.4 Kalender Ekonomi
├── 5. Insight
├── 6. Laporan
├── 7. Simulasi
│   ├── 7.1 Prop Firm
│   ├── 7.2 Backtest
│   └── 7.3 Trade Replay
├── 8. Akun & Koneksi
└── 9. Pengaturan
    ├── Profil & Keamanan (2FA, sesi, device)
    ├── Notifikasi
    ├── Tujuan (goals)
    └── Data (export, hapus akun)
```

**Navigasi:** sidebar (collapse di tablet, drawer di mobile) + topbar (account
selector, filter tanggal global, notifikasi bell, avatar). **Wayfinding:**
breadcrumb di halaman nested (Akun → Detail Akun).

---

# 6. PAGE TREE

| # | URL | Tujuan | Akses | Data utama | Action utama | Action sekunder | API | UI |
|---|---|---|---|---|---|---|---|---|
| P1 | `/` | Landing + fitur | Public | — | CTA Daftar/Masuk | lihat demo | — | hero, fitur grid |
| P2 | `/login` | Login | Public | — | login | lupa password | POST /auth/login | form |
| P3 | `/register` | Daftar | Public | — | daftar | — | POST /auth/register | form |
| P4 | `/forgot-password` | Reset | Public | — | kirim email | — | POST /auth/forgot | form |
| P5 | `/verify-email` | Verifikasi | Public | token | verifikasi | — | POST /auth/verify | status |
| P6 | `/app/dashboard` | KPI + chart | User | dashboard agg | ganti rentang | buka kalender P&L | GET /analytics/dashboard | stat grid, equity chart, kalender, insight cards |
| P7 | `/app/accounts` | Daftar akun | User | accounts | buat akun (demo/HF/konek) | edit/hapus | GET/POST /accounts | kartu akun, tombol HF, pairing |
| P8 | `/app/accounts/:id` | Detail akun | Owner | trades, equity | buka posisi/riwayat | sync manual | GET /accounts/:id | ringkasan + tab |
| P9 | `/app/positions` | Posisi terbuka | User | positions | tutup modal detail | refresh | GET /positions | tabel real-time |
| P10 | `/app/trades` | Riwayat + filter | User | trades | filter | export | GET /trades | tabel + filter bar |
| P11 | `/app/trades/:id` | Detail trade | Owner | trade+jurnal | tulis jurnal | MAE/MFE, replay | GET /trades/:id | drawer + jurnal form |
| P12 | `/app/journal` | Semua jurnal + kalender | User | journal | tulis jurnal baru | filter tag | GET /journal | kalender + daftar |
| P13 | `/app/analytics` | Metrik 21 | User | analytics | filter | export | GET /analytics/performance | KPI + chart + breakdown |
| P14 | `/app/analytics/mae-mfe` | MAE/MFE | User | mae_mfe | scatter filter | distribusi | GET /analytics/mae-mfe | scatter, histograms |
| P15 | `/app/analytics/score` | Skor 0–100 | User | score | breakdown komponen | riwayat skor | GET /analytics/score | gauge + komponen bar |
| P16 | `/app/insights` | Pola tersembunyi | User | insights | filter | ekspor insight | GET /insights | insight cards + confidence |
| P17 | `/app/calendar` | Kalender ekonomi | User | economic_events | filter impact | tandai event | GET /economic-calendar | tabel event + filter |
| P18 | `/app/reports` | Laporan + jadwal | User | reports | generate | jadwal otomatis | GET/POST /reports | daftar laporan, tombol PDF |
| P19 | `/app/goals` | Tujuan | User | goals | buat goal | progress | GET/POST /goals | kartu progress |
| P20 | `/app/prop-firm` | Simulator | User | prop_firm | pilih firm | tambah akun prop | GET/POST /prop-firm | status pass/fail, rules table |
| P21 | `/app/backtest` | Backtest | User | backtests | jalankan | simpan strategi | POST /backtests | wizard + hasil |
| P22 | `/app/replay` | Trade replay | User | replay | mainkan | pilih trade | POST /replays | player + chart |
| P23 | `/app/settings` | Profil, keamanan, notif | User | user | simpan | 2FA, sesi | GET/PATCH /me, /notifications | tabs |
| P24 | `/app/connector` | Status & pairing | User | devices | pairing | unduh connector | GET /connector/status | status + QR/code |
| P25 | `/admin` | Admin | Admin | users, logs | kelola user | quota | /admin/* | tabel admin |

---

# 7. USER FLOW (format: User → Frontend → API → Backend → DB → External → Response → UI)

**A. User baru (onboarding)**
Klik "Daftar" → form → `POST /auth/register` → validasi → insert users + kirim email verifikasi (Resend) → email diterima → `POST /auth/verify` → sesi dibuat → redirect `/app/dashboard` → empty state "Hubungkan MT5 atau coba Data Contoh".

**B. Register → Login → Dashboard**
`POST /auth/login` → cek hash argon2id + rate limit → buat access+refresh cookie, `users.session_version` baru → dashboard dimuat → `GET /analytics/dashboard` → daily_statistics kosong → empty state.

**C. Membuat Demo Account (sintetis)**
Klik "Data Contoh" → `POST /accounts` (kind=demo) → worker job `demo.generate` → generator sintetis membuat 60–90 hari trades realistis + equity snapshots → `GET /accounts` → kartu akun + toast → dashboard terisi otomatis.

**D. Menekan "Isi Akun Demo HF Markets"**
Klik tombol → `GET /meta/broker-presets` → response `{login:"49155931", server:"HFMarketsGlobal-Demo"}` → form akun terisi (password **tidak** diisi) → user isi password → simpan akun.

**E. Menghubungkan MT5**
Tab "Hubungkan MT5" → `POST /connector/pair` → pairing code 8 digit (TTL 5 mnt) → user buka connector desktop → masukkan code → `POST /connector/pair` (dari connector, HMAC) → device terdaftar ke user → status CONNECTED.

**F. Desktop Connector pertama kali aktif**
Connector start → cek konfigurasi (server URL + device key) → `GET /connector/config` → state PAIRING (jika belum) → AUTENTIKASI → `POST /connector/heartbeat` → state CONNECTED → user memilih akun MT5 yang aktif → `POST /connector/accounts` → mapping akun dibuat → SYNCING.

**G. Synchronization (inkremental)**
Connector `POST /connector/sync` (payload: deals baru + posisi + equity, ditandatangani) → validasi HMAC + user → upsert idempoten (unique ticket) → update positions, trades, deals, snapshots → enqueue recalc analytics → 200 `{inserted, updated}` → UI badge "Tersinkron HH:MM".

**H. Trade baru masuk**
MT5 membuka posisi → connector polling 5–10s → posisi baru terdeteksi → `POST /connector/sync` → insert positions → (jika user pilih notifikasi) notif "Trade dibuka" → UI tabel posisi update + toast subtle.

**I. Trade ditutup**
Deal close terdeteksi → upsert trades (status=closed, net_profit, swap, commission) → MAE/MFE final dihitung dari price path yang dikumpulkan → recalc daily_statistics + score → notif "Trade ditutup: +$X" → daftar riwayat update.

**J. User melakukan manual journal**
Buka detail trade → form jurnal → `POST /trades/:id/journal` → insert journal_entries + tags → recalc insight → modal sukses → jurnal tampil di timeline trade.

**K. User upload screenshot**
Pilih file → validasi client (tipe/ukuran) → `POST /trades/:id/screenshots` (multipart) → validasi server (magic bytes, strip EXIF, resize ≤1600px, ≤5MB) → simpan (lokal/R2) → thumbnail tampil.

**L. Analytics dihitung**
`GET /analytics/performance` → service cek `analytics_snapshots` valid (mtime) → jika basi: hitung dari trades + filter → simpan snapshot → response metrik.

**M. Insight dihasilkan**
Worker harian: ambil trades+journal → feature engineering → uji statistik (min 20 sampel, p<0.05) → insert insights → `GET /insights` → kartu insight + confidence badge.

**N. Weekly report dibuat**
Jadwal (Minggu 07:00) atau manual → worker: aggregate → render HTML → weasyprint PDF → simpan + link → email (Resend) + notifikasi in-app.

**O. Monthly report dibuat** — sama dengan N, rentang bulan, isi lebih lengkap (lihat §27).

**P. Telegram notification**
Trigger → worker → kirim `sendMessage` ke Bot API (rate limit per chat) → log ke notification_logs → update status delivered/failed.

**Q. Email notification** — trigger → Resend API → status log.

**R. Export PDF**
`POST /exports {type:pdf, scope}` → job RQ → render laporan → simpan file → status done + URL signed (TTL 24 jam) → UI tombol unduh aktif.

**S. Export Excel**
`POST /exports {type:excel}` → job → openpyxl (multi-sheet: trades, metrik, jurnal) → URL unduh.

**T. Prop Firm Simulator**
`POST /prop-firm/accounts` pilih preset → worker evaluasi harian: daily loss, max DD, profit target, min days → status Pass/Fail/In Progress + progress bar.

**U. Backtesting**
`POST /backtests {symbol, timeframe, range, strategy, params}` → worker: muat candles (history MT5 yang tersimpan / CSV import) → eksekusi aturan entry/exit → hitung fees/spread/slippage → simpan backtest_trades → laporan hasil (vs. live journal).

**V. Trade Replay**
`POST /replays {trade_id}` → ambil candles di window trade → player chart: play/pause/speed → user tandai entry/exit manual → simpan hasil replay → bandingkan dengan trade asli.

---

# 8. MT5 DESKTOP CONNECTOR ARCHITECTURE

## 8.1 Teknologi
- **Bahasa:** Python 3.12 + `MetaTrader5` lib (official), PyInstaller → `.exe` (Windows 10/11 64-bit).
- **Distribusi:** GitHub Releases + auto-update (cek versi → unduh zip → verifikasi checksum SHA-256 → ganti exe).
- **UI:** tray icon + jendela minimal (Tkinter) — status, tombol pairing, log.
- **Konfigurasi:** `connector.json` (server URL, device key) — dihasilkan dari pairing, tidak manual.

## 8.2 Komunikasi dengan MT5
- MetaTrader5 lib **read-only**: `initialize(login, server, password)` → `positions_get()`, `deals_get()`, `history_deals_get()`, `account_info()`, `symbol_info_tick()`.
- Polling 5–10s (posisi) + 30–60s (history baru). Event-driven opsional via `copy_ticks_from` untuk MAE/MFE path.
- **Credential MT5 disimpan di mesin lokal** (file terenkripsi, key dari DPAPI Windows) — **tidak dikirim ke server**.

## 8.3 Authentication & Pairing
- User login di web → klik "Hubungkan Connector" → server membuat **pairing code 8 digit (TTL 5 mnt, sekali pakai)**.
- Connector: user masukkan code → `POST /api/v1/connector/pair {code, client_id}` → server tukar code → **device_key** (random 32B, disimpan lokal, **hanya hash disimpan di server**) + **device_id**.
- Semua request connector → header `X-Device-Key` + body digest **HMAC-SHA256** (kunci = device_key) → anti-replay (timestamp ±60s + nonce).
- **Mapping akun:** setelah pairing, user memilih akun MT5 aktif → connector kirim `login + server` → server cek: (1) login belum dipakai user lain (unique), (2) user konfirmasi → `mt5_connections` dibuat. **Server TIDAK pernah menerima password MT5.**

## 8.4 Sync: pertama kali & inkremental
- **Pertama:** `history_deals_get(from=60 hari)` → kirim batch (maks 500 deal/batch, paginasi) → `POST /connector/sync {kind:"full"}` → server upsert.
- **Inkremental:** `deals_get()` (hari ini) + `history_deals_get(from=last_ticket_time)` → kirim `{since_ticket}` → server jawab `last_processed_ticket` → connector lanjut dari sana. **Duplikat dicegah:** `UNIQUE(trading_account_id, deal_ticket)` + upsert `ON CONFLICT DO NOTHING`.
- **Posisi:** `positions_get()` dikirim penuh tiap siklus → server diff vs `positions` (tutup otomatis saat tidak ada di list = partial close detection via volume berkurang).

## 8.5 Reconnect, offline, conflict
- **Heartbeat** 30s → `POST /connector/heartbeat` → server update `last_seen`. Jika >90s → status OFFLINE (badge UI, notif jika diaktifkan).
- **Offline mode:** connector simpan antrian payload di disk (`outbox.jsonl`), kirim ulang saat online (idempoten → aman).
- **Reconnect:** backoff exponensial (5s → 30s → 60s, max 5 mnt); coba login ulang MT5; server-side: `mt5_connections.state` diupdate oleh heartbeat.
- **Conflict resolution:** server adalah **otoritas**. Payload duplikat/stale ditolak (timestamp terlalu tua → 409 + minta state). Jika dua connector klaim akun sama → device kedua ditolak (akun sudah dipair).

## 8.6 Keamanan credential & data
- Password MT5: **hanya di lokal**, enkripsi DPAPI, tidak pernah di log.
- API key device: hash (Argon2) di server; HMAC untuk integrity.
- Payload: JSON, gzip, HTTPS (TLS 1.2+), nonce anti-replay.
- Server validasi: skema (Pydantic), ticket unik, tipe deal valid, simbol dikenal, angka finite, volume ≥ 0.

## 8.7 State Machine

```
DISCONNECTED ──(start)──► PAIRING ──(code valid)──► AUTHENTICATING ──(device_key ok)──► CONNECTED
      ▲                          │                                                  │
      │                     (expired)                                          (pilih akun)
      │                          ▼                                                  ▼
      │                     ERROR ◄────────────────────────────── SYNCING ──(selesai)──► SYNCED
      │                          ▲                                                       │
      └──(gagal)─────────────────┴─────────(jeda >90s / error)────────► RECONNECTING ────┘
```

Transisi: setiap transisi menulis event ke `connector_devices.events` + `mt5_connections.state`; UI memetakan state → badge (hijau SYNCED, kuning SYNCING, merah ERROR/OFFLINE).

# 9. DATABASE ARCHITECTURE

**PostgreSQL 16 (Neon managed).** ORM: SQLAlchemy 2 (typed, async). Migrasi: Alembic.
Konvensi: `id BIGSERIAL PK` · `user_id BIGINT NOT NULL REFERENCES users` di semua tabel tenant
(baris "tenant: user_id") · timestamp `timestamptz` **UTC** + `broker_tz` per akun ·
soft delete `deleted_at` di tabel user-facing · **retensi** di kolom terakhir.

## 9.1 Tabel inti (spec detail)

### users — profil + auth
PK `id`; fields: `username` uniq, `email` uniq, `password_hash` (argon2id), `email_verified_at` NULL,
`session_version` int (revoke semua sesi), `twofa_secret` NULL, `role` (user/admin), `locale`,
`base_currency`, `created_at`, `deleted_at` NULL. Index: email, username. Retensi: 90 hari setelah
soft-delete → hard delete (GDPR).

### sessions — sesi refresh token (device)
PK `id`; FK `user_id`; `refresh_token_hash` uniq, `device_name`, `ip`, `user_agent`, `expires_at`,
`revoked_at` NULL, `last_seen_at`. Index: user_id, refresh_token_hash. Retensi: 30 hari setelah expire/revoke.

### roles & permissions & user_roles — RBAC (fase 1: user/admin hardcoded; tabel siap untuk ekspansi)
PK `id`; `code` uniq; relasi M:N.

### trading_accounts — akun MT5 user
PK `id`; FK `user_id`, `broker_id`; fields: `name`, `login` (string, uniq per broker+server),
`server`, `kind` ('mt5'|'demo'|'manual'), `currency`, `leverage` int, `broker_tz` (offset menit),
`hf_preset` bool, `is_active` bool, `created_at`, `deleted_at`. Index: (user_id, is_active), (login, server) UNIQ.

### brokers — preset broker
PK `id`; `name` uniq, `server` uniq, `is_demo` bool, `popularity` int. Seed: HF Markets (`HFMarketsGlobal-Demo`).

### mt5_connections — koneksi connector↔akun
PK `id`; FK `user_id`, `trading_account_id` UNIQ, `connector_device_id`; `state` (enum §8.7),
`last_synced_at`, `last_deal_ticket` (inkremental), `last_error`, `created_at`. Index: state.

### connector_devices — perangkat connector
PK `id`; FK `user_id`; `device_name`, `device_key_hash` (argon2), `client_id` uniq, `pairing_code_hash`
+ `pairing_expires_at` NULL, `last_seen_at`, `version`, `ip`, `state`, `created_at`, `revoked_at` NULL.

### symbols & symbol_prices — simbol & harga terkini
PK `id`; `symbol` uniq, `base`, `quote`, `digits`, `point`; symbol_prices: FK `symbol_id`,
`bid`, `ask`, `spread`, `ts`. Retensi harga: 7 hari (rolling delete worker).

### candles — OHLCV (untuk chart/backtest/replay/MAE-MFE fallback)
PK `id`; FK `trading_account_id` (tenant), `symbol`; `tf` (M1..D1), `t` timestamptz, `o,h,l,c`, `v`.
**UNIQ(trading_account_id, symbol, tf, t)**. Index: (account, symbol, tf, t desc). Retensi: 2 tahun
+ config per user.

### trades — posisi tertutup (1 baris = 1 round-trip; deal berpasangan digabung)
PK `id`; FK `trading_account_id`, `user_id`; `ticket` (deal in) uniq per akun; `symbol`, `side`,
`volume`, `open_price`, `close_price`, `open_time`, `close_time`, `net_profit` NUMERIC(20,8),
`gross_profit`, `swap`, `commission`, `mae` NUMERIC NULL, `mfe` NUMERIC NULL, `mae_pct` NULL,
`mfe_pct` NULL, `r_multiple` NUMERIC NULL, `risk_amount` NULL, `source` ('sync'|'manual'),
`partial_closes` int default 0, `created_at`, `updated_at`.
**UNIQ(trading_account_id, ticket)**. Index: (account, close_time desc), (account, symbol), (account, side).
Retensi: seumur akun (default), user bisa hapus.

### positions — posisi terbuka (snapshot live)
PK `id`; FK `trading_account_id`; `ticket` uniq per akun, `symbol`, `side`, `volume`, `open_price`,
`open_time`, `current_price`, `floating_pnl`, `sl`, `tp`, `updated_at`. Retensi: dihapus saat posisi tutup.

### deals — semua deal mentah (audit + partial close)
PK `id`; FK `trading_account_id`; `deal_ticket` UNIQ per akun, `order_ticket`, `time`, `type`
(0 buy,1 sell,2 buy_close,3 sell_close), `symbol`, `volume`, `price`, `profit`, `swap`, `commission`,
`comment`, `external_id`. Index: (account, time desc).

### journal_entries — jurnal per trade (inti fitur jurnal)
PK `id`; FK `user_id`, `trading_account_id`, `trade_id` NULL (1:1 opsional); fields:
`entry_date`, `setup` (text), `emotion_before/emotion_during/emotion_after` (enum), `confidence` int 1–5,
`fear/greed/revenge/fomo/boredom` bool, `discipline` int 1–5, `rule_adherence` bool,
`reason_entry` text, `reason_exit` text, `notes` text, `lesson` text, `plan_match` bool NULL,
`created_at`, `updated_at`. Index: (user, entry_date), (trade_id).

### trade_tags — tag M:N (jurnal ↔ tag)
PK `id`; FK `journal_entry_id`, `tag_id`; **UNIQ(journal_entry_id, tag_id)**.

### tags — katalog tag user
PK `id`; FK `user_id`; `name` uniq per user, `color`, `created_at`.

### trade_notes — catatan tambahan bertimeline
PK `id`; FK `journal_entry_id`; `body`, `ts`.

### trade_screenshots — screenshot trade
PK `id`; FK `journal_entry_id`, `user_id`; `filename` uniq, `content_type`, `size`, `width`, `height`,
`storage` ('local'|'r2'), `path`, `thumb_path`, `created_at`. Retensi: 1 tahun atau saat akun dihapus.

### psychology_entries — tracker psikologi bebas (tidak harus terkait trade)
PK `id`; FK `user_id`, `trading_account_id` NULL, `journal_entry_id` NULL; `ts`, `mood`, `confidence`,
`focus`, `notes`. Index: (user, ts).

### account_snapshots / equity_snapshots / balance_snapshots — titik equity/balance
PK `id`; FK `trading_account_id`; `ts`, `value` (equity/balance), `comment` NULL.
**UNIQ(account, ts)** (per jam). Retensi: 5 tahun (dipakai equity curve).

### deposits & withdrawals — tracking dana
PK `id`; FK `trading_account_id`; `ts`, `amount`, `currency`, `method` NULL, `note`; `kind` enum.
Index: (account, ts).

### daily_statistics / monthly_statistics — agregasi per hari/bulan (cache analytics)
PK `id`; FK `trading_account_id`; `day`/`month`; fields: `net_profit`, `gross_profit`, `gross_loss`,
`win_count`, `loss_count`, `be_count`, `total_trades`, `win_rate`, `profit_factor`, `max_drawdown`,
`expectancy`, `best_trade`, `worst_trade`, `avg_win`, `avg_loss`, `r_sum`, `score` NULL,
`recalculated_at`. **UNIQ(account, day|month)**. Retensi: seumur.

### mae_mfe_records — ringkasan MAE/MFE per trade
PK `id`; FK `trade_id` UNIQ; `mae_pts`, `mfe_pts`, `mae_currency`, `mfe_currency`, `mae_pct`, `mfe_pct`,
`mae_r`, `mfe_r`, `path_source` ('ticks'|'candles'|'none'), `samples` int.

### analytics_snapshots — cache hasil perhitungan berat (perf, score, insight inputs)
PK `id`; FK `user_id`, `trading_account_id`; `kind` ('performance'|'score'|'insight'|'report_data'),
`params` jsonb, `payload` jsonb, `valid_until` timestamptz. Index: (account, kind).

### insights — pola terdeteksi
PK `id`; FK `user_id`, `trading_account_id`; `kind`, `title`, `description`, `confidence` NUMERIC(5,4),
`effect_size` NULL, `p_value` NULL, `sample_size`, `payload` jsonb, `recommendation` text,
`status` ('active'|'dismissed'), `created_at`. Index: (account, status, created_at desc).

### reports — laporan tersimpan
PK `id`; FK `user_id`, `trading_account_id` NULL; `kind` ('weekly'|'monthly'|'custom'), `period_start`,
`period_end`, `file_path`, `status` ('pending'|'done'|'failed'), `error` NULL, `created_at`.
Retensi: 1 tahun (file 90 hari).

### economic_events — kalender ekonomi
PK `id`; `ts`, `country`, `currency`, `event`, `impact` ('low'|'medium'|'high'), `actual` NULL,
`forecast` NULL, `previous` NULL, `source` ('import'|'api'), `created_at`. Index: (ts, impact).

### watchlists & watchlist_items
PK `id`; FK `user_id`; items: FK `watchlist_id`, `symbol`, `note` NULL; **UNIQ(watchlist_id, symbol)**.

### goals — tujuan trading
PK `id`; FK `user_id`; `title`, `metric` ('profit'|'winrate'|'trades'|'risk'|'score'), `target` NUMERIC,
`period` ('day'|'week'|'month'|'custom'), `start`, `end` NULL, `progress` jsonb NULL, `achieved_at` NULL.

### notifications, notification_preferences, notification_logs
PK `id`; FK `user_id`; notifications: `type`, `channel` ('inapp'|'telegram'|'email'), `title`, `body`,
`data` jsonb, `read_at` NULL, `created_at`; prefs: `user_id` UNIQ, `telegram_chat_id` NULL,
`email_enabled` bool, `jsonb triggers` (per event type: on/off + threshold); logs: FK `notification_id`,
`channel`, `status`, `provider_msg` NULL, `attempts`, `next_retry`. Retensi notif: 6 bulan.

### prop_firm_accounts, prop_firm_rules, prop_firm_metrics
PK `id`; FK `user_id`, `trading_account_id` NULL; accounts: `firm` (preset/custom), `status`
('in_progress'|'passed'|'failed'), `start_balance`, `current_balance`, `started_at`, `ended_at` NULL;
rules: FK `prop_firm_account_id`, `kind` (daily_loss|max_dd|profit_target|min_days|max_lot|news_restriction|
weekend_restriction), `value` NUMERIC, `unit`; metrics: FK `account_id`, `day`, `pnl`, `drawdown`,
`violation` NULL, `trading_days`. Index: (account, status).

### backtests, backtest_trades, trade_replays
backtests: PK `id`; FK `user_id`, `trading_account_id` NULL; `symbol`, `tf`, `strategy` jsonb,
`range_start/end`, `fees` jsonb (spread/slippage/commission), `status`, `result` jsonb, `created_at`.
backtest_trades: FK `backtest_id`, `entry/exit` fields, `net_profit`, `r`.
trade_replays: PK `id`; FK `user_id`, `trade_id` NULL; `candles_from/to`, `user_entries` jsonb,
`result` jsonb, `created_at`.

### exports — job export async
PK `id`; FK `user_id`; `kind` ('csv'|'excel'|'pdf'), `scope` jsonb, `status`, `file_path` NULL,
`expires_at` (24 jam), `created_at`. Retensi: file 24 jam, row 30 hari.

### audit_logs — jejak keamanan
PK `id`; `user_id` NULL, `action`, `entity`, `entity_id`, `ip`, `user_agent`, `payload` jsonb, `created_at`.
Index: (user_id, created_at desc). Retensi: 2 tahun.

### currency_rates — rate harian untuk konversi tampilan
PK `id`; `base`, `quote`, `rate`, `date`; **UNIQ(base, quote, date)**. Retensi: 1 tahun.

## 9.2 ERD ringkas (relasi utama)

```
users 1─N sessions · roles N─M permissions · users 1─N trading_accounts
trading_accounts 1─N {trades, deals, positions, journal_entries(→user), deposits,
                     withdrawals, snapshots, daily_statistics, mae_mfe_records,
                     mt5_connections, candles, economic_events(global)}
trades 1─0..1 journal_entries 1─N trade_tags N─M tags · journal 1─N trade_notes/screenshots
users 1─N {insights, goals, watchlists, notifications, exports, backtests, prop_firm_accounts, connectors}
```

---

# 10. MULTI-TENANCY

**Model:** tenant = **user** (bukan organisasi). Semua data milik persis satu user.

1. **Ownership strategy:** kolom `user_id` NOT NULL di semua tabel tenant + FK ke users.
2. **Authorization layer:** service layer menerima `current_user` (dari dependency auth) dan
   **selalu** menambahkan `user_id == current_user.id` di query — tidak pernah query by id saja.
3. **Row-Level Security (defense-in-depth, Phase 3):** enable RLS di tabel tenant,
   policy `USING (user_id = current_setting('app.user_id')::bigint)`; API set `app.user_id` per request.
   (Default fase 1: cukup layer service — RLS aktif saat production hardening.)
4. **API authorization:** resource id milik user lain → 404 (bukan 403, hindari enumerasi).
5. **Object storage:** path objek menyertakan user_id (`u{user_id}/...`); presigned URL dibatasi scope.
6. **DB-level protection:** unique constraint per tenant (`(user_id, name)`), query parameterized.

**Attack scenario:**
```
User A: GET /api/v1/trades/1001   (trade 1001 milik user B)
→ Middleware auth → current_user = A (id 7)
→ Service: SELECT * FROM trades WHERE id=1001 AND user_id=7
→ 0 baris → 404 {"detail":"Trade tidak ditemukan"}
```
Tidak ada jalur kode yang melakukan `WHERE id=?` tanpa `user_id` (dipaksa oleh pola repository;
diuji oleh test otomasi: memanggil endpoint resource user lain dengan token user A).

---

# 11. AUTHENTICATION & SECURITY

## 11.1 Desain auth
| Lapisan | Mekanisme |
|---|---|
| Password | Argon2id (memory 64MB, t=3) — `password_hash` |
| Sesi | **Access JWT 15 mnt (httpOnly cookie)** + **Refresh token 30 hari (httpOnly cookie, rotasi, disimpan hash di sessions)**; akses via `/auth/refresh`; cookie `Secure; SameSite=Lax; Path=/` |
| Session versioning | `users.session_version` — naikkan saat logout/ganti password → semua refresh token lama mati (pelajaran dari bug model lama) |
| CSRF | SameSite=Lax + `X-CSRF-Token` header (double-submit) untuk mutasi cookie-auth |
| Rate limiting | Redis sliding window: login 5/mnt/IP, register 3/jam/IP, API 120/mnt/user, connector 60/mnt/device |
| Brute-force | Rate limit + lockout exponensial (1m→5m→30m) per (email,IP) + audit log |
| MFA/2FA | TOTP (pyotp) — Phase 3, wajib untuk role admin |
| Email verification | Token 24 jam, sekali pakai; akun bisa login tapi dibatasi (read-only) sampai verified |
| API keys | Hanya untuk connector: `device_key` random 32B → hash Argon2 di DB; HMAC-SHA256 per request + nonce + timestamp |
| Secret management | Env vars di Render (dashboard); tidak pernah di repo; `.env.example` tanpa nilai |
| Webhook/connector security | HMAC signature `X-Sig: hex(hmac_sha256(device_key, ts + nonce + body))`, window ±60s, nonce sekali pakai (Redis SETNX) |
| File upload | Validasi: magic bytes (Pillow), ukuran ≤5MB, resize ≤1600px, strip EXIF, nama file acak (uuid), simpan di luar webroot |
| Screenshot security | Sama + otorisasi akses (owner only) + URL ber-token |
| XSS | React escape default; `dangerouslySetInnerHTML` dilarang; CSP header; sanitize input (Pydantic) |
| SQL injection | ORM + parameterized; ekspor query raw hanya via SQLAlchemy text dengan binding |
| CORS | Allowlist asal frontend (render domain) + localhost dev; tanpa `*` untuk kredensial |
| Audit log | Semua mutasi sensitif: login sukses/gagal, pairing, revoke, delete, export, admin action |
| Session revocation | Revoke semua (session_version++) / revoke satu (sessions.revoked_at) / revoke device |
| Device management | Halaman "Sesi aktif": nama device, IP, last_seen, tombol revoke |

## 11.2 Threat model sederhana

| Threat | Vektor | Mitigasi |
|---|---|---|
| Credential stuffing | login massal | rate limit + lockout + argo2id |
| Session hijack | cookie dicuri | httpOnly, Secure, rotasi refresh, revoke-by-device, deteksi IP anomali (log) |
| IDOR (akses data user lain) | endpoint resource id | tenant scoping + 404 + test otomasi |
| Connector spoof | pura-pura device sah | HMAC + device_key hash + nonce + pairing TTL |
| XSS | input user (jurnal/notes) | React escape + CSP + sanitasi rich text (allowlist) |
| CSRF | mutasi via cookie | SameSite + CSRF token |
| Upload jahat | screenshot | magic bytes + limit + EXIF strip + non-executable storage |
| API abuse | scraping | rate limit + quota per plan |
| Data breach DB | kompromi DB | hash argo2id, refresh hash, tenant scoping, backup terenkripsi |

---

# 12. ANALYTICS ENGINE

## 12.1 21 metrik + formula (semua dari trades tertutup, filter & rentang)

| # | Metrik | Formula | Real-time? |
|---|---|---|---|
| 1 | Net Profit | Σ net_profit | ya (via daily_statistics cache) |
| 2 | Gross Profit | Σ max(net_profit,0) | cache |
| 3 | Gross Loss | Σ min(net_profit,0) (abs) | cache |
| 4 | Profit Factor | gross_profit / gross_loss (∞ jika loss=0; undefined jika keduanya 0) | cache |
| 5 | Win Rate | wins / total (exclude breakeven, configurable) | cache |
| 6 | Loss Rate | 1 − win_rate | cache |
| 7 | Average Win | gross_profit / wins | cache |
| 8 | Average Loss | gross_loss / losses | cache |
| 9 | Expectancy | (win_rate × avg_win) − (loss_rate × avg_loss) | cache |
| 10 | Risk/Reward | avg_win / avg_loss | on-demand |
| 11 | R-Multiple | (net_profit − avg commission/swaps) / risk_amount; jika risk tak diketahui: net_profit / avg_loss (estimasi) | on-demand |
| 12 | Max Drawdown | max peak-to-trough equity curve (dari equity_snapshots) | cache harian |
| 13 | Average Drawdown | mean drawdown tiap streak rugi | on-demand |
| 14 | Recovery Factor | net_profit / max_drawdown | on-demand |
| 15 | Sharpe Ratio | (mean(r) − rf≈0) / std(r) × √n_period (harian) | on-demand |
| 16 | Sortino Ratio | (mean(r) − rf) / downside_deviation | on-demand |
| 17 | Payoff Ratio | avg_win / avg_loss (sama dengan R/R di sini; beda definisi jika pakai gross) | on-demand |
| 18 | Best/Worst Trade | max/min net_profit (rentang) | cache |
| 19 | Avg Trade Duration | mean(close_time − open_time) | on-demand |
| 20 | Winning Streak | max run wins | on-demand |
| 21 | Losing Streak | max run losses | on-demand |

**Strategi eksekusi:**
- **Realtime:** endpoint membaca `daily_statistics` (di-update worker saat sync selesai — latensi <10 detik).
- **On-demand:** metrik kompleks (Sharpe, streaks, MAE/MFE) dihitung saat request dengan cache 5 mnt di `analytics_snapshots` (parameter-hash key).
- **Snapshot:** `daily_statistics`/`monthly_statistics` di-recalc oleh worker setiap kali batch sync selesai atau jurnal berubah (debounce 60s).
- **Historical recalculation:** job `recalc.all(account_id)` idempoten — dijalankan manual dari UI ("Hitung ulang") atau otomatis saat import besar; menulis ulang daily/monthly + snapshots.

# 13. PERFORMANCE SCORE 0–100

**Model komponen (bobot):** Risk Management 20 · Consistency 20 · Profitability 20 ·
Drawdown Control 15 · Trade Quality 15 · Discipline & Psychology 10.

| Komponen | Sub-skor (0–1) | Normalisasi |
|---|---|---|
| Risk Management | 1 − min(1, avg_loss/risk_budget); risk_budget=1R; penalty jika ada trade risk >3% equity | clamp [0,1] |
| Consistency | 1 − normalized std(per-trade R); bonus jika win rate streak stabil | z-score → sigmoid |
| Profitability | sigmoid(expectancy_R / 0.5R) × 0.6 + sigmoid(profit_factor / 2) × 0.4 | sigmoid k=2 |
| Drawdown Control | 1 − min(1, max_dd / 20%); bonus jika max_dd < 10% | clamp |
| Trade Quality | 0.5×(1−avg_MAE/avg_MFE) + 0.25×plan_match_rate + 0.25×RR_avg_norm | clamp |
| Discipline | rule_adherence_rate × 0.5 + (1 − revenge_trades_ratio) × 0.3 + emotion_stability × 0.2 | clamp |

**Skor akhir = Σ(bobot × sub) × 100**, dibulatkan.

**Minimum data:** 20 trades tertutup (atau 10 jika < 30 hari). **Akun baru / data kurang:**
skor ditampilkan "—" + progress "X/20 trades untuk skor" (tidak menebak).

**Interpretasi (revisi agar adil untuk trader konservatif):**
| Skor | Label |
|---|---|
| 85–100 | Excellent |
| 70–84 | Strong |
| 55–69 | Good |
| 40–54 | Needs Improvement |
| <40 | Poor |

Revisi: ambang diturunkan karena komponen Discipline/Psychology (data jurnal sering
tidak lengkap) seharusnya **tidak menghukum** akun tanpa jurnal → bobot psikologi
diprorata ulang ke komponen lain jika <10 entri psikologi ("penalti data", ditampilkan transparan).

---

# 14. MAE / MFE ENGINE

**Definisi:** MAE = ekskursi merugikan maksimum dari harga entry sebelum exit;
MFE = ekskursi menguntungkan maksimum.

**Keterbatasan jujur:** API history MT5 **tidak memberi price path** — MAE/MFE tidak bisa
dihitung hanya dari deal. Solusi 3 tingkat:

1. **Live tick capture (terbaik):** connector mencatat harga simbol posisi terbuka tiap 5–10s
   (`symbol_info_tick`) → update `positions.mae/mfe` → final disimpan ke `mae_mfe_records` saat close.
2. **Fallback candles:** jika tidak ada tick (connector mati), hitung dari M1 candles dalam
   window open–close (server, job ringan) → `path_source='candles'`.
3. **Tanpa data:** `path_source='none'`, MAE/MFE NULL → tampil "tidak tersedia" + saran aktifkan connector.

**Unit:** simpan 4 bentuk: `_pts` (point simbol), `_currency`, `_pct`, `_r` (dibagi risk_amount).
**Visualisasi:**
- Scatter MAE vs MFE (X=MAE, Y=MFE, warna hasil) — kuadran ideal: MAE kecil, MFE besar.
- Histogram distribusi MFE & MAE per rentang; box plot MAE winner vs loser.
- **Optimal exit analysis:** `MFE − exit_price` = profit ditinggalkan; agregat "jika exit di
  50% MFE" → potensi profit (estimasi, ditandai eksperimen).

---

# 15. HIDDEN PATTERN / INSIGHT ENGINE

**Pipeline:** Input → Feature Engineering → Pattern Detection → Statistical Validation →
Insight + Confidence + Recommendation.

- **Input:** trades (rentang ≥ 30 hari) + journal (setup/emosi/tag) + psikologi + sesi (broker_tz).
- **Feature engineering:** per trade → day_of_week, session (Asia/London/NY), hour,
  holding_time bucket, risk bucket (0.5R/1R/2R), setup, emosi, tag, urutan streak,
  result setelah loss.
- **Pattern detection (template):**
  - Waktu: best/worst day-of-week, best session, best hour → `groupby → mean R`.
  - Simbol & arah: best/worst symbol, long vs short.
  - Setup: best/worst setup (perf + n).
  - Perilaku: revenge (trade ≤15 mnt setelah loss besar dgn risk naik), overtrading
    (>X trade/hari), consecutive losses (≥3), performa setelah loss vs setelah win.
  - Jurnal: performa per emosi/tag; plan_match rate.
- **Statistical validation (anti-korelasi kecil):**
  - **Min sample:** n ≥ 20 per segmen (n < 20 → tidak dipublish, ditampung sebagai "hint").
  - **Uji:** perbedaan mean R antar grup → **Welch t-test**, p < 0.05; kategori → chi-square.
  - **Effect size:** Cohen's d ≥ 0.5 (medium) — wajib, bukan hanya p.
  - **Multiple-comparison guard:** Bonferroni per batch.
- **Output:** `{kind, title, description, confidence, effect_size, p_value, sample_size, recommendation}`.
  Confidence = gabungan (p, effect size, n) → 0–100%; badge di UI; user bisa dismiss.
- **Anti-overfit:** insight dicek ulang tiap 7 hari (rolling window); hilang → status stale.

---

# 16. PSYCHOLOGY ENGINE

**Entitas:** `psychology_entries` per trade (before/during/after) + entry bebas harian.

Field per trade: `emotion_before/during/after` (enum: calm, confident, anxious, greedy,
fearful, frustrated, bored, euphoric, revengeful, neutral) · `confidence` 1–5 · flags:
`fear, greed, revenge, fomo, boredom` · `discipline` 1–5 · `rule_adherence` ·
`reason_entry`, `reason_exit` (text + preset chips: breakout, retest, news, FOMO, plan, dll).

**Analisis Psychology ↔ Trade ↔ Result:**
1. Agregasi: avg R, win rate, PF per emosi/flag/setup → tabel kontingensi.
2. Uji signifikansi (t-test per emosi vs baseline, min 20 sampel per grup).
3. **Perilaku berisiko:** revenge ratio (trade beruntun setelah loss dgn risk >1.5× median),
   FOMO ratio, overtrading days.
4. **Rule adherence:** % trade sesuai plan → korelasi dgn net profit (n ≥ 20).
5. Output: skor stabilitas emosi (0–100) + insight psikologi + rekomendasi
   (mis. "Setelah loss, rata-rata R kamu −0.8; pertimbangkan daily loss limit").

---

# 17. DASHBOARD DESIGN (wireframe)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ TOPBAR  [☰]  MT5 Journal   [Akun ▾]   [Rentang ▾]   [notif]   [user ▾]  │
├───────────┬──────────────────────────────────────────────────────────────┤
│ SIDEBAR   │  ACCOUNT SUMMARY (balance, equity, margin, leverage)        │
│ ·Dashboard│  ┌────────┬────────┬────────┬────────┬────────┬────────┐   │
│ ·Trading  │  │P&L hari│P&L bln │Win Rate│Profit  │Expect  │Score   │   │
│ ·Jurnal   │  │+$124,5 │+$1.820 │ 61,5%  │Factor  │+0,42R  │ 72     │   │
│ ·Analitik │  └────────┴────────┴────────┴────────┴────────┴────────┘   │
│ ·Insight  │  EQUITY CURVE ┌────────────────────────────────────────┐    │
│ ·Laporan  │               │   lightweight-charts (equity + DD area)│    │
│ ·Simulasi │               └────────────────────────────────────────┘    │
│ ·Akun     │  ┌─ POSISI TERBUKA (mini, 5) ─┐ ┌─ INSIGHT (2 kartu) ──┐   │
│ ·Setting  │  │ EURUSD BUY +$44 · XAU...   │ │ Best setup: BREAKOUT │   │
│           │  └────────────────────────────┘ │ (conf 87%)           │   │
│           │  P&L CALENDAR BULAN INI (heatmap) + daftar trade terbaru  │
└───────────┴──────────────────────────────────────────────────────────────┘
```

**Hierarki (UXPin):** KPI terpenting kiri-atas · 1 primary action per area ·
drill-down: klik hari di kalender → daftar trade hari itu → klik trade → drawer detail.
**Insight cards:** max 3, badge confidence, dismissible.
**Alerts:** daily loss threshold, connector offline, event high-impact (banner).

---

# 18. UI/UX DESIGN SYSTEM

> Dasar: `ui-foundation/` (tokens.css, demo.html) + MD3 + trading terminal density.
> **Wajib:** WCAG 2.2 AA, no-emoji icons (lucide), focus visible, loading≠disabled.

| Kategori | Spec |
|---|---|
| Font | Inter (UI) + JetBrains Mono (angka/terminal). Display 34px (2.5× body 14px) |
| Spacing | skala 4px (4/8/12/16/24/32/48) |
| Radius | 8/12/16/999; tombol pill MD3 |
| Shadow | 2 level (card, modal) + focus ring 2px primary |
| Warna | **Dark (default):** bg #0d1015, surface #14181f/#1a212c, text #e8eef6, aksen teal #2dd4a7, loss #f25f5c, warn #f5b544, info #4c9aff. **Light mode:** bg #f6f8fb, surface #ffffff, text #10151d, aksen sama (kontras ≥4.5:1 diverifikasi) |
| Kartu | gradient surface, border 1px #232b38, radius 16 |
| Tombol | primary (teal, text gelap), secondary (soft teal), ghost (border); min-height 44px; spinner loading (tidak meredupkan konten) |
| Input | label selalu di atas, min-height 46px, error + hint di bawah (role=alert) |
| Tabel | header uppercase 12px, tabular-nums, hover row, 1 pembeda per daftar, sticky header |
| Dropdown/Select | native + custom menu (keyboard nav), aria-expanded |
| Modal | overlay blur, role=dialog, Escape tutup, focus trap |
| Drawer | detail trade / jurnal dari kanan, 480px, overlay |
| Tabs | underline aktif, keyboard arrow nav |
| Badge/Chip | setup, emosi, tag, impact ekonomi (warna + ikon) |
| Alerts/Toast | 4 varian (info/success/warn/error), auto-dismiss 5s, aria-live polite |
| Charts | lightweight-charts (live/equity), Recharts (bar/histogram/scatter), cal-heatmap (kalender P&L + jurnal) |
| Empty states | judul + penjelasan + 1 CTA (memiliki viewport) |
| Loading | skeleton shimmer untuk halaman, spinner untuk aksi; loading ≠ disabled |
| Error states | pesan + aksi "coba lagi" + fallback data basi |

**Icon:** lucide (MIT, inline SVG). **Motion:** 150–200ms ease-out; respect `prefers-reduced-motion`.

---

# 19. RESPONSIVE DESIGN

| Elemen | Desktop ≥1024 | Tablet 768–1023 | Mobile <768 |
|---|---|---|---|
| Sidebar | tetap 240px | collapse ikon 64px | drawer off-canvas (hamburger) |
| Stat grid | 6 kolom | 3 kolom | 2 kolom (P&L full-width) |
| Tabel | penuh, sticky header | scroll horizontal | scroll horizontal + kartu mode (kolom inti) |
| Equity chart | penuh | penuh | tinggi 220px |
| Kalender P&L | 7 kolom | 7 kolom | 7 kolom kecil (tap = modal detail) |
| Filter bar | inline | wrap | drawer filter |
| Modal/Drawer | centered 520px / drawer 480px | sama | full-screen sheet |
| Topbar | lengkap | akun + notif saja | ikon saja |

**Mobile-first CSS (min-width breakpoints); PWA:** target touch 44px, safe-area insets,
status bar themed.

# 20. REST API ARCHITECTURE

**Base:** `/api/v1` · Format: JSON (`application/json`) · Error: RFC 7807
`{"detail": ..., "code": ...}` · Pagination: `?limit&offset` → `{items, total}` ·
Auth: cookie JWT untuk UI, `X-Device-Key`+HMAC untuk connector ·
Rate limit: 120/mnt/user, 5/mnt login, 60/mnt device.

| Method & Path | Auth | Otorisasi | Request | Response | Validasi | Error | DB op |
|---|---|---|---|---|---|---|---|
| POST /auth/register | — | public | username, email, password | 201 {id} | email format, pass ≥8 | 409 duplikat, 422 | insert users + kirim verifikasi |
| POST /auth/login | — | public | email, password | 200 {user} + cookie | rate limit | 401 | cek hash, buat sessions, session_version++ |
| POST /auth/logout | cookie | user | — | 204 | — | — | revoke session, session_version++ |
| POST /auth/refresh | cookie | user | refresh token | 200 + rotasi | TTL | 401 | cek hash+version, putar token |
| POST /auth/forgot | — | public | email | 202 | rate limit | 200 selalu | token reset → email |
| POST /auth/reset | — | public | token, password | 204 | TTL 15mnt | 400 | update hash, revoke sesi |
| POST /auth/verify | — | public | token | 200 | TTL 24j | 400 | email_verified_at |
| GET /auth/sessions | cookie | user | — | list sesi | — | — | select |
| DELETE /auth/sessions/:id | cookie | user | — | 204 | id milik user | 404 | revoke |
| GET /accounts | cookie | user | — | list + status koneksi | — | — | select |
| POST /accounts | cookie | user | {name, login, server, kind, broker_id?} | 201 | login unik | 409 | insert + enqueue demo-gen jika kind=demo |
| PATCH /accounts/:id | cookie | owner | patch fields | 200 | — | 404 | update |
| DELETE /accounts/:id | cookie | owner | — | 204 | — | 404 | soft delete + revoke koneksi |
| POST /accounts/:id/sync | cookie | owner | — | 202 | — | — | enqueue sync request (ke connector via long-poll? cukup status) |
| GET /meta/broker-presets | cookie | user | — | [{login, server}] | — | — | select brokers |
| GET /positions | cookie | user | ?account_id&symbol | {items, total} | — | — | select live |
| GET /trades | cookie | user | filters+page | {items, total, summary} | — | — | select + aggregate |
| GET /trades/:id | cookie | owner | — | detail + deals + journal + mae_mfe | — | 404 | select |
| POST /trades | cookie | user | manual trade fields | 201 | angka valid | 422 | insert (source=manual) |
| PATCH /trades/:id | cookie | owner | edit manual trade | 200 | — | 404 | update + recalc |
| DELETE /trades/:id | cookie | owner | — | 204 | — | 404 | soft delete + recalc |
| POST /trades/:id/journal | cookie | owner | setup, emosi, notes, tags… | 201 | tag ≤8 | 422 | upsert journal + tags |
| GET /journal | cookie | user | ?from&to&tag | list | — | — | select |
| POST /trades/:id/screenshots | cookie | owner | multipart file | 201 | ≤5MB, image | 413/415 | validasi + simpan |
| GET /psychology | cookie | user | ?range | list + summary | — | — | select + agg |
| POST /psychology | cookie | user | entry | 201 | enum valid | 422 | insert |
| GET /analytics/dashboard | cookie | user | ?account&from&to | {summary, equity[], cal[], open[], insights[]} | — | — | agg + cache |
| GET /analytics/performance | cookie | user | filters | 21 metrik + breakdown | — | — | cache/on-demand |
| GET /analytics/score | cookie | user | ?account | {score, components[], label, needed} | min data | — | hitung + cache |
| GET /analytics/mae-mfe | cookie | user | filters | {scatter[], dist[], optimal_exit} | — | — | agg |
| GET /insights | cookie | user | ?status | list | — | — | select |
| POST /insights/:id/dismiss | cookie | owner | — | 204 | — | 404 | update status |
| GET /economic-calendar | cookie | user | ?date&impact | list | — | — | select |
| GET /reports | cookie | user | list | — | — | — | select |
| POST /reports | cookie | user | {kind, period} | 202 job | — | — | enqueue report |
| GET /reports/:id | cookie | owner | — | status + url | — | 404 | select |
| GET /goals · POST /goals · PATCH /goals/:id | cookie | user/owner | — | CRUD | — | — | select/insert/update |
| GET /prop-firm | cookie | user | list + status | — | — | — | select + eval |
| POST /prop-firm/accounts | cookie | user | {firm, rules} | 201 | — | — | insert |
| GET /prop-firm/presets | cookie | user | — | presets | — | — | select |
| POST /backtests | cookie | user | {symbol, tf, range, strategy} | 202 job | — | — | enqueue |
| GET /backtests/:id | cookie | owner | — | status + result | — | 404 | select |
| POST /replays | cookie | user | {trade_id?} | 201 | — | — | siapkan candles |
| POST /replays/:id/finish | cookie | owner | user_entries | 200 result | — | — | hitung hasil |
| GET /watchlist · POST /watchlist | cookie | user | symbol | CRUD | simbol valid | — | select/insert |
| GET /quotes | cookie | user | ?symbols | quotes | — | — | select symbol_prices |
| POST /connector/pair | cookie | user | — | {code} | — | — | buat pairing_code (hash) |
| POST /connector/pair/confirm | device | device | {code, client_id} | {device_id, device_key} | TTL 5mnt | 410 expired | tukar code |
| POST /connector/sync | device | device | {kind, deals[], positions[], equity} | {inserted, updated, last_ticket} | HMAC+skema | 422/409 | upsert batch + recalc enqueue |
| POST /connector/heartbeat | device | device | {state, version, accounts[]} | {config} | HMAC | — | update last_seen |
| GET /connector/status | cookie | user | — | devices + states | — | — | select |
| GET /transactions (deposit/withdrawal) | cookie | user | CRUD | — | — | — | select/insert |
| POST /exports | cookie | user | {kind, scope} | 202 job | — | — | enqueue |
| GET /exports/:id | cookie | owner | — | status + url (signed, 24j) | — | 404 | select |
| GET /notifications | cookie | user | ?unread | list | — | — | select |
| PATCH /notifications/:id | cookie | owner | {read} | 200 | — | — | update |
| GET/PATCH /notifications/prefs | cookie | user | prefs | 200 | — | — | select/update |
| POST /notifications/telegram/link | cookie | user | {code} | 200 | TTL 10mnt | 400 | hubungkan chat |
| GET /me · PATCH /me | cookie | user | profile | 200 | — | — | select/update |
| POST /me/delete | cookie | user | password | 202 | — | 401 | soft delete + anonymize job |
| GET /admin/users | cookie | admin | ?q | list | role admin | 403 | select |
| PATCH /admin/users/:id | cookie | admin | quota/status | 200 | role admin | 403 | update |
| GET /healthz | — | public | — | {status, db, redis} | — | — | ping |
| GET /connector/download | cookie | user | — | redirect exe | — | — | GitHub release |

---

# 21. EXTERNAL SERVICES

| Service | Fungsi | Provider kandidat | API | Biaya | Rate limit | Fallback | Risiko |
|---|---|---|---|---|---|---|---|
| MT5 | sumber data | MetaTrader5 lib (via connector) | Python API | gratis | — | mode demo sintetis | terminal harus jalan |
| Market data | quotes/candles (opsional) | OANDA (v20) / Dukascopy CSV | REST/CSV | gratis | 150/min | data dari connector saja | akun OANDA opsional |
| Economic calendar | event news | Forex Factory (import manual) → Trading Economics (paid) nanti | CSV/API | gratis→$ | — | import manual CSV | scraping rapuh/ToS → **adapter + manual** |
| Telegram | notifikasi | Bot API | HTTP | gratis | 30 msg/s/bot | email + in-app | bot diblokir → retry/backoff |
| Email | verifikasi, reset, laporan | **Resend** (default), SendGrid, SMTP | REST | gratis 3k/bln | 2/s | queue retry | spam folder |
| Object storage | screenshot | lokal → **Cloudflare R2** (Phase 2) | S3-compatible | gratis 10GB | — | lokal | latency |
| PDF | laporan | **weasyprint** (server-side) | Python | gratis | — | HTML view | font/emoji edge case |
| Excel | export | **openpyxl** | Python | gratis | — | CSV | — |
| Auth/email | verifikasi & reset | Resend (di atas) | — | — | — | — | — |
| Monitoring | error/uptime | **Sentry** (error) + UptimeRobot (uptime) | SDK/REST | free tier | — | log saja | — |

**Aturan:** semua layanan eksternal diisolasi di belakang adapter interface —
tidak ada kode yang memanggil provider langsung; provider bisa diganti tanpa ubah logika.

---

# 22. DEMO ACCOUNT (mode "Data Contoh" + "Isi Akun Demo HF Markets")

**Dua mode (keputusan DR-03):**

1. **Data Contoh (sintetis, instan):** user baru tanpa MT5 bisa eksplor penuh.
   - `POST /accounts {kind:"demo"}` → worker `demo.generate`:
   - Struktur: balance $10.000, leverage 1:100, mata uang USD, broker_tz UTC+2 (EET).
   - Generator: 60–90 hari kalender trading (weekday), 120–220 trades tertutup
     (win rate 45–55%, R distribution realistic: −1R..−3R losses, +0.5R..+3R wins),
     spread/swap/commission masuk, 0–3 posisi terbuka, equity path wajar (DD 5–15%),
     3 deposit (awal, +$5.000 di tengah, withdrawal kecil), beberapa entri jurnal
     & psikologi (5–10), tags (breakout, retest, news), MAE/MFE dari harga sintetis.
   - Semua data **random seed per user** (deterministik per akun) + label jelas
     "DATA CONTOH — bukan akun asli" di dashboard (badge DEMO).
2. **Isi Akun Demo HF Markets:** tombol → `GET /meta/broker-presets` →
   `{login:"49155931", server:"HFMarketsGlobal-Demo"}` → form terisi; user mengisi
   password sendiri → akun kind=mt5 siap dipair dengan connector.

---

# 23. PROP FIRM SIMULATOR

**Engine evaluasi (worker, harian):** untuk tiap `prop_firm_accounts` status in_progress:
1. Hitung `daily_statistics` hari itu → cek **daily loss limit** (mis. 5% dari balance awal hari) → violate → FAIL.
2. Cek **max drawdown** (relatif start balance atau high-watermark) → violate → FAIL.
3. Cek **profit target** tercapai → PASS (jika min trading days terpenuhi).
4. Akumulasi **trading days** (hari dengan ≥1 trade) → jika < min_days → tetap In Progress.
5. Check **news/weekend restriction** (jika rules aktif): trade dalam window → warning (bukan fail, konfigurasi).

**Parameter rule:** starting balance · profit target (%) · daily loss limit (%) ·
max drawdown (%) · min trading days · leverage · max lot · max risk per trade (%) ·
news restriction (bool + window) · weekend restriction (bool).

**Preset:** FTMO (Challenge/Verified), The5ers (Hyper), FundedNext (Stellar), MFF — sebagai
seed data `prop_firm_rules`; user bisa buat custom. **UI:** kartu status
(Pass / Fail / In Progress + progress bar per rule + tabel metric harian + warning list).

---

# 24. BACKTESTING + TRADE REPLAY

**Pemisahan tegas dari data live:** semua modul simulasi bekerja pada data **copy**
(candles & history snapshot), tidak pernah menulis ke `trades` live; hasil disimpan di
`backtests`/`backtest_trades`/`trade_replays` — tidak mengubah statistik live.

**Backtest (rule-based, tanpa eksekusi kode user):**
- Dataset: candles dari `candles` (history MT5 via connector) + import CSV (Dukascopy/HistData) → `symbol_prices`/`candles` dengan `source='import'`.
- Strategy: preset rule builder (EMA cross, breakout N-bar, support/resistance manual, S/R + filter sesi) — parameter JSON; eksekusi kode user **tidak** didukung di v1 (keamanan).
- Eksekusi: iterasi candle → sinyal entry/exit → **posisi sizing** (risk % balance) →
  **fees model:** spread (config/point), commission, **slippage** (pips, config) → equity curve.
- Anti lookahead: sinyal hanya dari candle yang sudah closed; **spread dikenakan saat entry**.
- Hasil: metrik lengkap (sama engine §12) + per-trade list + perbandingan "backtest vs live journal" (jika akun sama).

**Trade Replay (player interaktif):**
- `POST /replays {trade_id}` → ambil candles window open±30% → player UI (lightweight-charts):
  play/pause/speed 1×/2×/5×/10×, scrub, mark entry/exit manual, exit reason.
- Selesai → `POST /replays/:id/finish {user_entries}` → hitung hasil simulasi →
  bandingkan dengan trade asli (harga exit user vs aktual) → tampil di detail trade.
- Data replay murni di `trade_replays` — **tidak memengaruhi** metrik live.

---

# 25. REPORTING

**Isi laporan mingguan & bulanan:** ringkasan P&L · win rate · PF · max drawdown ·
best/worst trade · best/worst day & symbol · distribusi R · psikologi (emosi dominan,
rule adherence) · MAE/MFE ringkas · performance score + riwayat · insight aktif +
rekomendasi · progress goals · lampiran: equity curve + kalender P&L.

**Mode:**
- **On-demand:** tombol "Buat Laporan" → job RQ → status pending→done → PDF + link (24 jam) + email.
- **Terjadwal:** worker cron — mingguan (Minggu 07:00 user-tz), bulanan (tanggal 1) →
  simpan `reports` + email otomatis (jika pref aktif).
- **Realtime:** ringkasan laporan = endpoint yang sama dengan dashboard (data segar).

**Teknis:** template Jinja2 HTML → weasyprint PDF; angka selalu tabular, tanda +/- jelas,
mata uang per akun (konversi opsional).

---

# 26. NOTIFICATION SYSTEM

**Kanal:** in-app (pusat notifikasi + banner) · Telegram (Bot API) · Email (Resend).

**Trigger & default:**
| Trigger | In-app | Telegram | Email |
|---|---|---|---|
| Trade dibuka/ditutup | ✅ | ✅ (ops) | — |
| Daily loss threshold (mis. −2%) | ✅ | ✅ | — |
| Drawdown threshold | ✅ | ✅ | — |
| Laporan mingguan/bulanan siap | ✅ | — | ✅ |
| Goal tercapai | ✅ | ✅ | — |
| Prop firm warning | ✅ | ✅ | — |
| Sync error / connector offline >5 mnt | ✅ | ✅ | ✅ |
| Kalender ekonomi high-impact (H-1) | ✅ | ops | — |

**Arsitektur:** trigger → enqueue job → `notifications` (in-app selalu) + dispatch
per channel sesuai `notification_preferences` (jsonb: per-event {enabled, threshold,
channels}) → `notification_logs` (status, attempts, retry backoff 5×) → rate limit
Telegram per chat (1/s) + email (queue).

**Telegram linking:** user chat bot `/start` dengan kode sekali pakai 8 digit (10 mnt)
→ `telegram_chat_id` tersimpan → tidak perlu nomor HP.

---

# 27. EXPORT SYSTEM (CSV / Excel / PDF)

- **Alur:** `POST /exports {kind, scope}` → validasi scope (rentang, akun, filter) →
  job RQ async → generate (CSV: csv stdlib; Excel: openpyxl multi-sheet [Trades, Deals,
  Journal, Metrik, Equity]; PDF: weasyprint) → simpan file (lokal/R2) → status done →
  `GET /exports/:id` → **signed URL TTL 24 jam** (token acak di tabel exports, bukan
  file publik) → UI tombol unduh aktif.
- **Keamanan:** download butuh auth (cookie) + token; file dihapus job pembersih 24 jam;
  ekspor membatasi baris (max 50.000, sisanya peringatan "data terpotong").
- **Privasi:** semua kolom sensitif (password, API key) tidak pernah diekspor.

---

# 28. PWA

| Aspek | Keputusan |
|---|---|
| Installability | manifest.json (name, icons 192/512, theme #0d1015, display standalone, start_url /app) |
| Service Worker | Workbox (generateSW): precache shell, cache-first aset (hash), network-first navigasi, stale-while-revalidate API GET |
| Cache | versi `mt5j-v1` (pelajaran dari SW lama: jangan absolute path, selalu relatif; hapus cache lama otomatis) |
| Offline strategy | **Offline-capable:** shell, baca cache terakhir, jurnal manual + screenshot (queue IndexedDB → Background Sync saat online), export status. **Online-required:** harga, sync, posisi, kalender ekonomi, insight — tampil "data terakhir HH:MM" + banner offline |
| Push notification | **Phase 3** (VAPID + Web Push; iOS tidak konsisten → Telegram kanal utama) |
| Background sync | journal queue → `sync` event → replay ke API |
| Responsive | lihat §19 |

---

# 29. DEVOPS

```
Browser → Cloudflare CDN (ops) → Render Web (FastAPI) → Neon PostgreSQL
                                     → Redis (Render) → RQ Worker
External: Resend · Telegram · R2 · Sentry · UptimeRobot
```

| Aspek | Keputusan |
|---|---|
| Environment | dev (lokal, docker-compose: postgres+redis), staging (Render preview), production |
| Env vars | `.env.example`; Render dashboard; **tidak pernah** di repo |
| CI/CD | GitHub Actions: lint+test (pytest, vitest) → build → deploy (Render Deploy Hook); connector: build PyInstaller → GitHub Release (auto-update) |
| Migrasi DB | Alembic: `alembic upgrade head` di deploy hook (job khusus, sebelum web start) |
| Backup | Neon: PITR otomatis + dump mingguan ke R2 (pg_dump, retensi 30 hari) |
| Monitoring | `/healthz` (db+redis) diping UptimeRobot 5 mnt · Sentry (error API+web) · log structured JSON (request_id, user_id, latency) |
| Alerting | Sentry alert → Telegram admin; uptime down → email admin |
| Rollback | Render: redeploy versi sebelumnya (image tag); migrasi: hanya additive/backward-compatible di production |
| Disaster recovery | RTO < 1 jam (redeploy + PITR), RPO 5 mnt (Neon WAL); dokumen runbook di `docs/runbook.md` |

---

# 30. TECHNOLOGY STACK (perbandingan + final)

| Lapisan | Opsi | Skor (1–5: scalability, dev speed, maintainability, cost, ecosystem, MT5 compat, security, deploy) | Final |
|---|---|---|---|
| Frontend | React+Vite+TS · Next.js · Svelte · vanilla | React+Vite: 4,5,5,5,5,5,5,5 = 4.9 → **pilih** (keputusan user) | **React 19 + Vite + TS + Tailwind** |
| Backend | FastAPI · Flask · Node/Nest | FastAPI: 4,5,5,5,5,5,5,5 = 4.9 → **pilih** (keputusan user) | **FastAPI (Python 3.12)** |
| Database | PostgreSQL · MySQL · SQLite | PG: 5,4,5,4,5,5,5,5 = 4.8 | **PostgreSQL 16 (Neon)** |
| Cache | Redis · memcached | Redis: 5,5,5,4,5,5,5,5 | **Redis** (rate limit + queue) |
| Queue | RQ · Celery · Dramatiq | RQ: 3,5,5,5,4,5,5,5 = 4.6 → cukup untuk scope ini | **RQ** (Celery jika butuh cron kompleks — ganti adapter) |
| Charts | lightweight-charts · Recharts · chart.js | LW: 5 (live) + Recharts 4 (statis) | **lightweight-charts + Recharts** |
| Auth | session cookie · JWT · OAuth lib | JWT+refresh: 4,4,4,5,5,5,5,4 | **JWT access + refresh rotasi + session versioning** |
| Object storage | lokal · R2 · S3 | R2: 4,4,5,5,5,5,5,5 | **lokal (fase 1) → Cloudflare R2 (fase 2)** |
| Connector | Python+MetaTrader5 lib | satu-satunya yang kompatibel MT5 | **Python + PyInstaller** |
| Hosting | Render · Railway · VPS | Render: 4,5,5,4,4,5,5,5 = 4.6 (keputusan user) | **Render + Neon** |
| Email | Resend · SendGrid · SMTP | Resend: 4,5,5,5,5,5,5,5 | **Resend** |
| PWA | Workbox · vite-plugin-pwa | vite-plugin-pwa: 5,5,5,5,5,5,5,5 | **vite-plugin-pwa (Workbox)** |

# 31. DEPENDENCY MAP

```
Auth → User → Trading Account → MT5 Connection (pairing) → Trades/Deals → Analytics → Score/Insight/Reports
                                     ↓                                              ↑
                              Watchlist/Quotes/Candles ──────────────────────────┘
Journal & Psychology ──(terkait trades / bebas)──► Insight & Laporan
Market data (import CSV) ──► Backtest ──► Replay
Trades + Analytics ──► Prop Firm Simulator · Goals
Semua modul ──► Export · Notifikasi (lintas)
```

**Urutan wajib:** Auth → Accounts → Connector → Trades → Analytics → (Score/Insight/Report
paralel setelah Analytics) → Simulasi (butuh Trades+Candles) → Notifikasi/Export (butuh
hampir semua, tapi API-nya bisa dibangun awal).

---

# 32. MVP vs PHASE 2 vs PHASE 3 vs ADVANCED

Kriteria: dependency · business value · complexity · risk · validation value.

## MVP (rilis pertama — "app bisa dipakai")
| Fitur | Alasan |
|---|---|
| Auth (register/login/logout/verifikasi/reset) | prasyarat semua |
| Accounts + Demo sintetis + tombol HF | onboarding tanpa MT5 (validasi nilai) |
| Connector pairing + sync + heartbeat | fitur inti "web pasti + auto-sync" |
| Open/Closed positions + riwayat + detail | data inti |
| Jurnal manual (notes/setup/emosi/tag) + screenshot | diferensiasi inti (jurnal trading) |
| Dashboard P&L + equity + kalender P&L | value terlihat segera |
| 21 metrik (dasar) + filter | analisis tanpa eksotik |
| Export CSV | murah, dipakai trader serius |
| Settings profil + sesi + notif in-app | keamanan dasar |

## PHASE 2
| Fitur | Alasan |
|---|---|
| MAE/MFE (tick capture + candles fallback) | butuh data path (butuh connector stabil) |
| Performance score | butuh ≥20 trades + metrik stabil |
| Laporan mingguan/bulanan + PDF + email | butuh analytics + journal lengkap |
| Multi-account penuh (selector, agregasi) | butuh schema stabil; kompleksitas menengah |
| Kalender ekonomi (import manual → API) | independen; nilai untuk jadwal trading |
| Telegram notifikasi | murah, value tinggi |
| Export Excel/PDF | extend export MVP |
| Deposit/withdrawal tracking | sederhana; melengkapi laporan |

## PHASE 3
| Fitur | Alasan |
|---|---|
| Insight engine | butuh data ≥30 hari + jurnal (validasi statistik) |
| Psikologi analitik (korelasi) | butuh jurnal konsisten |
| Prop firm simulator | butuh analytics stabil; aturan berubah-ubah (maintenance) |
| Backtesting + Trade Replay | kompleksitas tinggi, risiko lookahead; butuh candles |
| Goal tracking | sederhana, bisa maju |
| PWA penuh (push, background sync) | polish |
| 2FA · RLS · R2 · admin panel · audit UI | hardening |

## ADVANCED (pasca production)
OAuth Google · Web Push · multi-currency conversion penuh · AI insight (LLM) ·
strategi backtest scriptable (sandbox) · plan berbayar (quota) · kalender ekonomi API berbayar.

---

# 33. DEVELOPMENT TREE (monorepo)

```
mt5-journal/
├── apps/
│   ├── web/                      # React 19 + Vite + TS + Tailwind (PWA)
│   │   ├── src/
│   │   │   ├── app/              # router + providers (auth, query, theme)
│   │   │   ├── pages/            # per URL (§6)
│   │   │   ├── components/       # ui/ (design system) + feature/ (per modul)
│   │   │   ├── features/         # dashboard, trades, journal, analytics, insight,
│   │   │   │                     #   reports, prop-firm, backtest, replay, settings…
│   │   │   ├── lib/              # api client, hooks, utils
│   │   │   ├── stores/           # account selector, filters, toasts
│   │   │   └── styles/           # tokens.css (dari ui-foundation)
│   │   └── public/               # icons, manifest
│   ├── api/                      # FastAPI
│   │   └── app/
│   │       ├── main.py           # app factory, middleware (CORS, CSRF, rate limit)
│   │       ├── core/             # config, security, db, redis, logging
│   │       ├── models/           # SQLAlchemy (per modul)
│   │       ├── schemas/          # Pydantic
│   │       ├── services/         # auth, accounts, trades, journal, analytics,
│   │       │                     #   insight, psychology, reports, prop_firm,
│   │       │                     #   backtest, export, notifications, demo
│   │       ├── api/              # routers v1
│   │       └── jobs/             # task functions (RQ)
│   ├── worker/                   # RQ worker (import dari api.app.jobs) + cron (schedule)
│   └── connector/                # Python desktop connector
│       ├── mt5_client.py         # MetaTrader5 read-only wrapper
│       ├── syncer.py             # full/incremental sync + outbox
│       ├── pairer.py             # pairing + device key (DPAPI)
│       ├── tracker.py            # tick capture MAE/MFE
│       ├── updater.py            # auto-update (GitHub Releases)
│       └── main.py               # tray + state machine
├── packages/
│   ├── db/                       # shared: models + alembic (dipakai api & worker)
│   ├── analytics/                # pure math: metrics, score, mae/mfe, insight stats
│   ├── types/                    # shared TS types (dari OpenAPI)
│   └── config/                   # env schema + constants
├── infra/
│   ├── docker-compose.dev.yml
│   ├── render.yaml
│   ├── alembic.ini
│   └── scripts/                  # backup, seed, demo-gen
├── docs/                         # blueprint, runbook, API (openapi.json)
└── .github/workflows/            # ci.yml, connector-release.yml
```

Tidak ada folder yang tidak dipakai: `packages/types` dihasilkan dari OpenAPI
(openapi-typescript), `packages/ui` digabung ke `apps/web/src/components/ui`.

---

# 34. IMPLEMENTATION ORDER (PHASE 0–16)

| Phase | Objective | Dependency | Deliverables | Acceptance criteria | Risks |
|---|---|---|---|---|---|
| 0 Architecture | setup repo + standar | — | monorepo, tokens, CI, docker-compose, alembic init | `make dev` jalan; lint+test hijau | scope creep |
| 1 Foundation | config, DB, health | 0 | models inti (users, accounts, sessions), healthz, logging | migrasi idempoten; healthz 200 | migrasi retak |
| 2 Authentication | auth penuh | 1 | register/login/logout/refresh/verify/forgot/reset, rate limit, session mgmt | uji: logout revoke; brute force diblok; cookie httpOnly | session bug (pelajaran: session_version) |
| 3 Database & accounts | akun + demo | 2 | CRUD accounts, brokers seed, demo generator, presets HF | akun demo 60–90 hari data dalam <5s | generator bias |
| 4 MT5 Connector | pairing + sync | 3 | connector exe, pairing, heartbeat, sync full/inkremental, outbox | 10k deal import tanpa duplikat; offline resume | duplikat/race |
| 5 Trading Data | posisi/riwayat/detail | 4 | positions, trades, deals, manual entry, screenshots, watchlist | posisi live <10s; manual entry tervalidasi | partial close |
| 6 Dashboard | P&L UI | 5 | stat grid, equity, kalender P&L, filter global, account selector | angka cocok dengan SQL manual | timezone/DST |
| 7 Analytics | 21 metrik | 6 | engine metrik, daily stats, snapshot cache, filter | metrik = kalkulasi referensi (test golden) | float/precision |
| 8 Journal | jurnal + psikologi | 6 | journal CRUD + tags + screenshot, psychology tracker, kalender jurnal | jurnal 1 klik dari trade; tag filter jalan | schema jurnal berubah |
| 9 Reports | laporan + export | 7,8 | report engine, PDF, Excel, jadwal cron, email | laporan sesuai isi §25; PDF valid | layout PDF |
| 10 Advanced Analytics | score + MAE/MFE + insight | 7,8 | score engine, mae/mfe (tick+candles), insight engine | skor konsisten; insight min 20 sampel | overfit insight |
| 11 Prop Firm | simulator | 7 | presets, evaluasi harian, status | contoh FTMO pass/fail benar | rules berubah |
| 12 Backtesting/Replay | simulasi | 5,10 | backtest engine, CSV import, replay player | hasil = kalkulasi referensi; replay terpisah dari live | lookahead |
| 13 Notifications | telegram+email | 2,9 | prefs, triggers, telegram link, logs | semua trigger terkirim + retry | rate limit |
| 14 PWA | instal + offline | 1 | manifest, SW, offline journal queue, (push fase 3) | Lighthouse PWA ≥90; offline entry tersinkron | SW cache lama |
| 15 Production | hardening | semua | 2FA, RLS, R2, admin, audit UI, sentry, backup, runbook | pentest dasar lulus; rollback teruji | — |
| 16 Stabilisasi | bug + perf | semua | load test, edge case pass, dokumentasi | §37 edge cases hijau | — |

---

# 35. ACCEPTANCE CRITERIA (contoh resmi per fitur)

```
FEATURE: MT5 Synchronization
SUCCESS:
- connector authenticated (device key + HMAC valid)
- account identified & dipetakan ke user yang tepat
- historical trades terimport (batch, paginasi)
- duplicate prevention: import ulang → 0 duplikat (unique ticket)
- incremental sync: hanya deal baru yang masuk
- connection recovery: mati 10 mnt → online kembali, state benar
FAILURE:
- unauthorized access → 401/403
- duplicate trade → ditolak ON CONFLICT, tidak crash
- corrupted payload → 422 + log, tidak merusak data lama
- wrong account mapping → ditolak (login sudah ter-pair)

FEATURE: Manual Trading Journal
SUCCESS: entri tersimpan dengan trade/tanpa trade · tag ≤8 · screenshot terpasang ·
filter tag/rentang benar · edit & hapus tercatat audit
FAILURE: trade milik user lain → 404 · file bukan gambar → 415 · emosi invalid → 422

FEATURE: Performance Score
SUCCESS: ≥20 trades → skor 0–100 dengan breakdown komponen · akun baru → "—" + progress ·
recalc setelah sync baru mengubah skor
FAILURE: data < minimum → jangan paksa angka · pembagian nol → null aman

FEATURE: Multi-Tenant Isolation
SUCCESS: user A tidak melihat id resource user B (404) · test otomasi lintas user hijau
FAILURE: kebocoran → test gagal (wajib di CI)
```

---

# 36. EDGE CASES (daftar lengkap + penanganan)

| Edge case | Penanganan |
|---|---|
| Duplicate trade (sync ulang) | UNIQ(trading_account_id, ticket) + ON CONFLICT DO NOTHING |
| Partial close | deal pasangan volume < original → update trades (volume sisa, avg close), `partial_closes++`; posisi baru utk sisa |
| Multiple positions simbol sama (hedging) | posisi per ticket (MT5 hedging) — jangan gabung |
| Hedging vs netting | netting: deal pasangan simetris → pasangan via `position_id`/`external_id` |
| Swap & commission | disimpan per deal + per trade (net_profit = profit+swap+commission) |
| Spread/slippage | harga entry = harga deal (sudah termasuk spread); slippage hanya di backtest |
| Symbol suffix (EURUSD.a, XAUUSDm) | `symbols` store suffix; normalisasi filter via `base_symbol` |
| Broker timezone & DST | `broker_tz` per akun; storage UTC; sesi dari broker_tz (calendar-aware) |
| Disconnected MT5 | connector state OFFLINE; heartbeat >90s; queue outbox |
| Duplicate connector (2 device klaim akun sama) | device kedua ditolak 409; revoke dari UI |
| Deleted account | soft delete; trades tetap (retensi) atau ikut hapus sesuai pilihan user |
| Negative balance | ditampilkan apa adanya; metrik tetap konsisten (jangan clamp) |
| Deposit/withdrawal | jangan masuk ke net_profit; hanya balance/equity curve + laporan |
| Account reset broker (server hilang) | deteksi: login/server sama tapi riwayat kosong → tanya user "reset?" → archive akun, buat baru |
| Timezone mismatch (server vs broker) | semua komparasi via timestamptz UTC |
| Currency conversion | rate harian di `currency_rates`; konversi = tampilan saja, metrik tetap mata uang akun |
| Missing candle (gap/offline) | backtest: lewati candle hilang (log); MAE/MFE fallback: path_source='none' |
| API outage (connector down / external) | job retry backoff; UI banner "data terakhir" |
| Duplicate webhook/payload | nonce sekali pakai (Redis SETNX) + idempoten upsert |
| Stale market price | timestamp quote; quote >5 mnt → label "stale" |
| Screenshot terlalu besar | limit 5MB + resize 1600px + kompresi |
| Malicious upload | magic bytes + strip EXIF + nama uuid + non-executable storage |
| User deletion | soft delete → job anonymize (email → hash, username → deleted_uuid) → hard delete 90 hari |
| GDPR/data deletion | ekspor semua data user (zip) sebelum hapus; hapus = permanen |
| Database failure | Neon managed + healthz + retry pool; rollback deploy |
| Tambahan | trade terbuka saat weekend (swap 3x) · leverage berubah tengah posisi · akun zeroing (margin call) · order teredit (SL/TP) tak memengaruhi P&L · time server ≠ broker · float precision (NUMERIC(20,8) + Decimal) · DST ganda (EET/EEST) |

---

# 37. CRITICAL DESIGN QUESTIONS (risiko arsitektur)

**CRITICAL**
| Problem | Kenapa penting | Solusi | Rekomendasi | Konsekuensi |
|---|---|---|---|---|
| MAE/MFE butuh price path, history MT5 tidak menyediakan | fitur inti bisa kosong | tick capture live / candles fallback / "tidak tersedia" | 3 tingkat (§14), tampilkan source | tanpa connector aktif, MAE/MFE kosong — dokumentasi di UI |
| MT5 hanya jalan di Windows + terminal login | "web pasti" terancam jika terminal mati | connector polling + outbox; metaapi.cloud (opsional) | connector dulu (terbukti); MetaApi alternatif P2 | user harus punya terminal jalan untuk sync live |
| Distribusi connector exe ke user non-teknis | onboarding patah | PyInstaller + auto-update + checksum + panduan | GitHub Releases + updater | butuh dokumentasi yang baik |
| Backtest lookahead bias | hasil menyesatkan | rules-only, candle closed, spread saat entry, disclaimer | batasan tegas di UI | tidak 100% realistis — disclaim |

**HIGH**
| Problem | Solusi | Rekomendasi |
|---|---|---|
| Sync concurrency (connector ganda / race upsert) | transaction per batch + unique + retry | unique constraints + ON CONFLICT |
| Rate limit vs sync berat multi-akun | limit terpisah per device | endpoint sync pakai limit device |
| Insight overfit / korelasi palsu | min 20 sampel + p<0.05 + d≥0.5 + Bonferroni | wajib, bukan opsional |
| Storage screenshot membesar | resize + R2 + retensi | limit + pembersih harian |
| Schema berubah setelah user punya data | Alembic additive-only di production | aturan tim |

**MEDIUM:** cron timezone per user · email bounce · long-poll vs polling (pilih polling) ·
PWA cache invalidation (versi SW + hapus cache lama) · RQ worker scale (1 worker cukup awal).

**LOW:** bahasa UI campuran · favicon branding · analytics internal (skip, privasi).

---

# 38. TESTING STRATEGY

| Lapisan | Alat | Cakupan wajib |
|---|---|---|
| Unit (analytics/score/insight) | pytest | **golden tests**: metrik vs kalkulasi referensi; skor; MAE/MFE; insight validator |
| API | pytest + httpx | semua endpoint: auth, otorisasi lintas user (404), validasi, rate limit |
| Multi-tenant | test khusus | tiap resource: token user A → id user B → 404 (list semua resource) |
| Connector | pytest (MT5 mock) | state machine, outbox, duplikat, partial close, reconnect |
| Frontend | vitest + RTL | komponen kunci, hooks filter, journal form; Playwright e2e (login→demo→jurnal→export) |
| PWA | Lighthouse CI | installability ≥90, offline journal e2e |
| Load | locust (fase 15) | 200 user concurrent read; sync batch 10k deal |

---

# 39. RISKS (ringkasan)

1. **MAE/MFE tanpa connector aktif** → kosong (dikelola §14).
2. **Connector exe distribusi** → auto-update + checksum + docs.
3. **Kalender ekonomi scraping** → adapter + manual import (jangan dependency).
4. **Backtest akurasi** → rules-only + disclaimer + golden tests.
5. **Insight palsu** → ambang statistik ketat.
6. **Scope 35 fitur** → phasing MVP→P3 + acceptance per fase (ponytail: YAGNI per fase).
7. **Keamanan** → threat model §11.2 + hardening Phase 15.

---

# 40. DECISION REQUIRED — SEMUA SUDAH DIKUNCI (LOCKED)

> ✅ **2026-08-29: seluruh keputusan dikunci via Council of High Intelligence +
> ponytail. Register lengkap + alasan di `KEPUTUSAN-FINAL.md`.** Ringkas:

| ID | Keputusan | FINAL |
|---|---|---|
| DR-01 | Stack | React+FastAPI (locked) |
| DR-02 | Deploy | Render+Neon (locked) |
| DR-03 | Demo | dua mode (locked) |
| DR-04 | Backtest data | connector+CSV (locked) |
| DR-05 | Auth | email/password + verifikasi; OAuth tidak di v1 |
| DR-06 | Email | Resend |
| DR-07 | Screenshot | lokal → R2 (fase 15) |
| DR-08 | Economic calendar | import manual CSV; TANPA scraping |
| DR-09 | Market data | connector saja |
| DR-10 | Prop firm | preset + custom (fase 3) |
| DR-11 | Bahasa | Indonesia (istilah EN) |
| DR-12 | Multi-currency | per akun; konversi tidak dijadwalkan |
| DR-13 | User deletion | soft delete + anonymize |
| DR-14 | PDF | weasyprint |
| DR-15 | Push notif | **Web Push di-skip total**; Telegram+email+in-app |
| DR-16 | MetaApi | tidak di v1; didokumentasikan |
| DR-17 | Free tier quota | 2 akun, 10k trades/user |
| DR-18 | Light mode | Phase 2 (swap token) |
| DR-19 | Admin panel | Fase 15 |
| DR-20 | Testing | golden tests + multi-tenant test wajib di CI |

---

# 41. FINAL RECOMMENDED ARCHITECTURE (ringkas)

**Monorepo 5 app (web / api / worker / connector) + 4 packages (db, analytics, types, config).**
Web = React 19 PWA (MD3 + trading terminal, dark default + light mode). API = FastAPI
stateless, JWT+refresh cookie, tenant-scoped, rate limited. DB = PostgreSQL 16 (Neon),
SQLAlchemy 2 + Alembic, `user_id` di semua tabel (RLS fase 3). Worker = RQ (sync, recalc,
report, export, notif, cron). Connector = Python read-only, pairing code + HMAC,
incremental sync idempoten, MAE/MFE tick capture, auto-update. Deploy = Render + Redis +
R2, CI/CD GitHub Actions, Sentry + UptimeRobot, backup Neon PITR + pg_dump.

**Prinsip yang menjaga blueprint tetap sehat:** API-first · tenant-aware · idempoten ·
worker-heavy · adapter untuk semua external · golden tests untuk math · phasing
MVP→P3 dengan acceptance criteria · ponytail (YAGNI) per fase.

> **Next:** Phase 0–1 scaffolding (repo kosong `itzranke/Metatrader5-PNL`), dengan
> aturan `AGENTS.md` aktif. Siap mulai development atas persetujuan user.



