# 🔒 KEPUTUSAN-FINAL
## MT5 Trading Journal & Analytics Platform — Semua Keputusan Terkunci

**Status:** LOCKED (final) · **Tanggal:** 2026-08-29
**Metode:** scan seluruh percakapan + Council of High Intelligence (panel 5, 2 ronde) +
ponytail (YAGNI) + skill UI/UX + riset. Menggantikan semua status "terbuka" di BLUEPRINT.md §40.

---

## 1. CATATAN COUNCIL (ringkas)

**Pertanyaan:** Finalisasi jalur: (a) MVP 9 fitur, (b) rewrite React+FastAPI dengan reuse
maksimal, (c) kunci DR-05…DR-17.

**Ronde 1 — posisi:**
- **Socrates (asumsi):** Tantang asumsi "rewrite total" — data & komputasi lama
  (journal_math, connector, pola sync) sudah teruji dan **harus di-reuse**, bukan
  ditulis ulang. Yang baru hanyalah frontend React + lapisan PG. MVP harus menguji
  value inti (sync + jurnal), bukan kelengkapan fitur.
- **Feynman (first principles):** Sistem = data (trades) + komputasi (metrik) +
  tampilan. Hanya tampilan yang benar-benar perlu dibangun baru. PG benar (concurrency
  multi-user, backup managed). MAE/MFE jangan diklaim dari history saja — batasan
  3 tingkat di blueprint sudah benar.
- **Kahneman (bias):** Ancaman: planning fallacy (35 fitur = 3× estimasi), availability
  (fitur yang baru diriset terasa penting), optimisme. **Pre-mortem:** proyek gagal
  jika (1) MVP kegedean, (2) connector bermasalah di mesin user nyata, (3) fitur eksotis
  (backtest/prop) makan waktu sebelum inti jalan. De-bias: kunci MVP + uji connector
  dengan user nyata paling awal.
- **Torvalds (ship it):** Mulai Phase 0–1 sekarang. Jangan tulis ulang yang bekerja.
  Backtest tidak boleh dibangun sebelum trades+candles stabil. Web Push → skip.
- **Meadows (sistem):** Loop inti = user → trades → insight → perbaikan. Fitur yang
  memperkuat loop: sync otomatis, jurnal cepat, metrik jujur, demo sintetis — sudah
  benar di MVP. Kalender ekonomi/notifikasi = sinyal input, fase 2 tepat.

**Ronde 2 — vote:**
| Keputusan | Socrates | Feynman | Kahneman | Torvalds | Meadows | Hasil |
|---|---|---|---|---|---|---|
| MVP 9 fitur (tanpa eksotik) | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5 LOCK** |
| Rewrite React+FastAPI + reuse backend lama | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5 LOCK** |
| DR-05…17 default (dgn amandemen) | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5 LOCK** |
| Web Push (DR-15) → SKIP total | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5 LOCK** |
| Kalender ekonomi: manual CSV, TANPA scraping | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5 LOCK** |
| Langkah segera: mulai Phase 0–1 | ✅ | ✅ | ✅ | ✅ | ✅ | **5/5 LOCK** |

**Amandemen council yang diterima:** (1) Web Push dibatalkan total — Telegram+email
cukup, iOS tidak konsisten (ponytail: jangan bangun yang tak terpakai). (2) Light mode
maju ke Phase 2 (murah — cukup swap token). (3) MetaApi tidak di v1, hanya didokumentasikan.

---

## 2. REGISTER KEPUTUSAN TERKUNCI (semua DR)

| ID | Keputusan | FINAL (locked) |
|---|---|---|
| DR-01 | Stack | **React 19 + Vite + TS + Tailwind** (web) · **Python FastAPI** (api) · PostgreSQL 16 · Redis · RQ |
| DR-02 | Deployment | **Render** (web+api+worker) + **Neon** (PG managed) + Redis Render; R2 fase 15 |
| DR-03 | Demo | **Dua mode**: "Data Contoh" sintetis + tombol "Isi Akun Demo HF Markets" (isi login+server saja, password user sendiri) |
| DR-04 | Backtest data | **Riwayat connector + import CSV** (Dukascopy/HistData); tanpa API eksternal |
| DR-05 | Auth | email/password + **email verification** + forgot/reset; JWT access 15mnt + refresh rotasi 30 hari (cookie httpOnly); **session versioning**; OAuth TIDAK di v1 |
| DR-06 | Email | **Resend** (free tier 3k/bln) |
| DR-07 | Screenshot | **Lokal disk** (fase 1) → Cloudflare R2 (fase 15); validasi magic-bytes, ≤5MB, resize 1600px, strip EXIF |
| DR-08 | Kalender ekonomi | **Import manual CSV** (fase 2) + adapter interface; **TANPA scraping** (risiko ToS/rapuh); API berbayar = keputusan terpisah nanti |
| DR-09 | Market data | **Connector saja**; eksternal (OANDA) = opsional, tidak dijadwalkan |
| DR-10 | Prop firm | **Preset (FTMO, The5ers, FundedNext) + custom rules**; fase 3 |
| DR-11 | Bahasa | **Indonesia** (istilah trading EN: BUY/SELL/swap/commission) |
| DR-12 | Multi-currency | Tampil **sesuai mata uang akun**; konversi tampilan = opsional, tidak dijadwalkan |
| DR-13 | User deletion | **Soft delete + anonymize** (GDPR-lite), hard delete 90 hari |
| DR-14 | PDF | **weasyprint** (Python, di worker) |
| DR-15 | Push notif | **SKIP Web Push total** — Telegram (fase 2) + email + in-app saja |
| DR-16 | MetaApi cloud | **Tidak di v1**; didokumentasikan sebagai alternatif P2 (MT5 tanpa terminal) |
| DR-17 | Quota free tier | **2 akun, 10.000 trades/user** (config env, bisa diubah) |
| DR-18 (baru) | Light mode | **Phase 2** (swap token; dark = default) |
| DR-19 (baru) | Admin panel | **Fase 15** (hardening), bukan MVP |
| DR-20 (baru) | Testing | Golden tests untuk semua math (metrik/score/MAE-MFE/insight) + test multi-tenant lintas user wajib di CI |

---

## 3. SCOPE MVP TERKUNCI (9 fitur + kriteria keluar)

1. Auth: register / login / logout / verifikasi email / forgot-reset / sesi+device
2. Accounts: CRUD + akun "Data Contoh" sintetis + tombol "Isi Akun Demo HF Markets"
3. Connector: pairing (code 8 digit) + heartbeat + sync full/inkremental + outbox offline
4. Trading data: open positions · closed positions · riwayat · detail trade · manual trade entry
5. Jurnal manual: notes / setup / emosi / tag (≤8) / screenshot / edit-hapus
6. Dashboard: stat grid (P&L hari/bulan, win rate, PF, expectancy, score slot) ·
   equity curve · kalender P&L bulanan · posisi mini · insight slot (kosong di MVP)
7. Analitik: **21 metrik** + filter (simbol/arah/tag/rentang) + daily/monthly statistics cache
8. Export CSV (async job, TTL 24 jam)
9. Settings: profil, keamanan (ganti password, sesi), notif in-app

**Exit criteria MVP ("app hidup"):**
- User baru: daftar → email verifikasi → login → buat akun Data Contoh → lihat P&L
  + equity + kalender → tulis jurnal + tag → export CSV. **Tanpa membaca dokumentasi.**
- User MT5: buat akun → download connector → pairing → sync (10.000 deal, 0 duplikat)
  → posisi live <10s → riwayat + metrik benar (golden test).
- Keamanan: test otomasi lintas user 100% hijau (404 untuk resource milik user lain).

---

## 4. ARSITEKTUR & REUSE TERKUNCI

**Monorepo (BLUEPRINT §33):** `apps/{web,api,worker,connector}` + `packages/{db,analytics,types,config}`.

**Reuse dari backup `/home/user/mt5-tracker` (TIDAK ditulis ulang):**
| Aset lama | Nasib |
|---|---|
| `journal_math.py` (metrik/analitik) | → `packages/analytics` (uji golden, port ke SQLAlchemy) |
| `connector.py` + pola sync idempoten | → `apps/connector` (tambah HMAC, pairing code, MAE/MFE tick) |
| `db.py` session versioning + rotate | → `packages/db` (pola dipertahankan) |
| `demo_data.py` (generator) | → `apps/api` service demo (generator sintetis diperluas) |
| `ui-foundation/` tokens + aturan UI | → `apps/web` design system |
| Pelajaran SW v5 (path relatif, network-first, hapus cache lama) | → vite-plugin-pwa config |
| `Dockerfile`/`render.yaml` | → `infra/` (adaptasi FastAPI+worker) |

**TIDAK di-reuse:** frontend vanilla JS (ditulis ulang di React), SQLite (→ PG), Flask (→ FastAPI).

**Stack final (BLUEPRINT §30):** React 19+Vite+TS+Tailwind · FastAPI · PG 16 (Neon) ·
Redis · RQ · lightweight-charts+Recharts · Resend · weasyprint · openpyxl ·
PyInstaller connector · Render · Sentry.

---

## 5. PHASING TERKUNCI & GATE

| Fase | Isi | Gate keluar |
|---|---|---|
| **0–1** | Repo, monorepo, tokens, CI, docker-compose dev, Alembic init, models inti, healthz | `make dev` jalan; lint+test hijau; migrasi idempoten |
| **2** | Auth penuh + rate limit + session mgmt | uji logout-revoke, brute force, cookie httpOnly |
| **3** | Accounts + demo sintetis + preset HF | demo 60–90 hari <5 detik |
| **4** | Connector (pairing, sync, outbox) | 10k deal 0 duplikat; offline resume |
| **5** | Trading data + manual entry + screenshots | posisi <10s; upload aman |
| **6–7** | Dashboard + 21 metrik | angka = golden test; timezone/DST benar |
| **8** | Jurnal + psikologi + kalender jurnal | jurnal 1 klik; filter tag |
| **9** | Laporan + export CSV/Excel/PDF + cron + email | PDF valid; jadwal jalan |
| **10** | Score + MAE/MFE + Insight | ambang statistik; skor konsisten |
| **11** | Prop firm | preset FTMO pass/fail benar |
| **12** | Backtest + replay | hasil = referensi; terpisah dari live |
| **13** | Telegram + notifikasi | semua trigger + retry |
| **14** | PWA (tanpa Web Push) | Lighthouse ≥90; offline journal tersinkron |
| **15** | Hardening: 2FA, RLS, R2, admin, Sentry, backup | pentest dasar lulus |
| **16** | Stabilisasi + load test | edge cases hijau |

**TIDAK dijadwalkan (cut, ponytail):** Web Push · OAuth · AI/LLM insight ·
backtest scriptable · multi-currency konversi penuh · scraping kalender ekonomi ·
MetaApi v1 · plan berbayar.

---

## 6. REPO & WORKFLOW TERKUNCI

- Repo `itzranke/Metatrader5-PNL` (public, kosong — 1 commit `fd3988d`) → diisi dari
  Phase 0–1, **tanpa riwayat lama** (backup lokal hanya referensi).
- Push memakai PAT (ingat: **revoke token setelah selesai**); identitas
  `itzranke` / `255658937+itzranke@users.noreply.github.com`.
- Aturan kerja `AGENTS.md` aktif (ponytail full + council untuk keputusan besar).
- Branch: `main` (production-ready), PR via GitHub Actions test gate.
- Setiap phase: commit kecil + acceptance criteria fase hijau sebelum lanjut.

---

## 7. RENCANA SEGERA (Phase 0–1 checklist)

1. Scaffold monorepo di repo kosong: `apps/` + `packages/` + `infra/` + `docs/`.
2. `packages/config` env schema; `infra/docker-compose.dev.yml` (postgres+redis).
3. `packages/db`: SQLAlchemy 2 models inti (users, sessions, accounts, trades,
   journal…) + Alembic init + migrasi pertama.
4. `apps/api`: FastAPI skeleton + healthz + middleware (CORS, rate limit, logging).
5. `apps/web`: Vite React skeleton + tokens dari `ui-foundation/` + router + PWA base.
6. CI: pytest + vitest + lint; push awal; Pages/dokumen README baru.

**Gate Phase 0–1:** semua item hijau → lanjut Phase 2 (Auth).
