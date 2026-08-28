# 📚 RISET — Skill UI/UX, Preseden, Studi Kasus & Sumber Daya

Ringkasan menyeluruh hasil pencarian GitHub + internet untuk membangun ulang
MT5 Journal dari nol. Semua sumber dipelajari dan prinsipnya sudah dipakai
di folder `ui-foundation/`.

---

## 1️⃣ SKILL UI/UX DARI GITHUB (ditemukan & digunakan)

### A. Skill agent AI untuk desain (paling relevan untuk kita)
| Repo | ⭐ | Isi |
|---|---|---|
| **nextlevelbuilder/ui-ux-pro-max-skill** | 121k | Skill AI desain: design intelligence profesional multi-platform |
| **plugin87/ux-ui-agent-skills** | 806 | "Senior Design Architect": DTCG design tokens, 42 komponen, WCAG 2.2, 138 design system, rule yang bisa dijalankan |
| **stevembarclay/pencilplaybook** | — | Playbook desain: perceptual psychology + guardrails anti "AI slop" |
| **JimLiu/baoyu-design** | — | Skill desain agent: mockup/prototype HTML self-contained |

**Aturan yang langsung KITA GUNAKAN (dari plugin87/ux-ui-agent-skills):**
- ❌ **No emoji sebagai ikon UI** — pakai lucide icons / kata-kata
- Empty state harus "memiliki" viewport-nya (jangan mengambang)
- **Loading ≠ disabled** (jangan redupkan elemen saat loading)
- Feedback tidak boleh mendahului kebenaran (toast hanya untuk yang nyata)
- Daftar panjang butuh satu pembeda (differentiator)
- Overflow tersembunyi harus ada isyarat visual
- **Komposisi dulu, baru styling**; display type 2.5× body text
- Type scale yang berani, kartu tidak boleh 40 biji seragam
- DTCG design tokens sebagai standar token

### B. Design system & component library
| Repo | ⭐ | Catatan |
|---|---|---|
| vmware-archive/clarity | 6.392 | Design system scalable + accessible (web components) |
| inkline/inkline | 1.462 | UI components library developer-friendly |
| Trendyol/baklava | 1.385 | Design system konsisten multi-brand |
| WTTJ/welcome-ui | 673 | Design system React + Tailwind |
| hunvreus/basecoat | 4.266 | Komponen Tailwind, works with any stack |
| franken-ui/ui | 2.605 | HTML-first, UIkit 3 + LitElement |
| DavidHDev/canvas-ui | 4.353 | Canvas/WebGL components |
| kokonut-labs/kokonutui | 2.060 | Komponen Tailwind + shadcn + Motion |

### C. Template dashboard siap pakai
| Repo | ⭐ |
|---|---|
| ColorlibHQ/AdminLTE | 45.563 (Bootstrap, klasik) |
| epicmaxco/vuestic-admin | 10.954 (Vue) |
| Kiranism/next-shadcn-dashboard-starter | 6.900 (Next.js + shadcn + Tailwind, AI-friendly) |
| devias-io/material-kit-react | 5.586 (Material UI) |
| themesberg/flowbite-admin-dashboard | 2.879 (Tailwind + Flowbite) |
| cruip/tailwind-dashboard-template | 2.836 (Mosaic Lite) |
| TailAdmin/free-nextjs-admin-dashboard | 2.535 |
| justboil/admin-one-vue-tailwind | 2.464 (dark mode) |

---

## 2️⃣ "COUNCLE" — hasil pencarian

**TERPECAHKAN:** yang dimaksud user ternyata **"council"** →
`0xNyk/council-of-high-intelligence` (lihat Bagian 8 — sekarang ter-install).
Cari pertama kali tidak menemukannya karena kata "councle" memang typo.
Interpretasi tambahan tetap dipakai: **concise UI + counsel UX**
(microcopy membimbing) — sudah masuk ke `ui-foundation/`.

## 8️⃣ SKILL BARU TER-INSTALL (atas permintaan user)

| Repo | ⭐ | Apa itu | Status |
|---|---|---|---|
| **DietrichGebert/ponytail** | **115k** | Skill agent AI: "lazy senior dev" — tangga YAGNI (jangan buat yang tak perlu → reuse → stdlib → native → dep terpasang → 1 baris → kode minimum), bug fix di akar, komentar `ponytail:` untuk potongan sudut, SATU runnable check per logika non-trivial | ✅ ter-install di `skills/ponytail`, diaktifkan via `AGENTS.md` (mode full) |
| **0xNyk/council-of-high-intelligence** | **4.2k** | Skill deliberasi multi-perspektif: 18 anggota (Aristotle, Socrates, Sun Tzu, Ada, Feynman, Torvalds, Kahneman, Meadows, Munger, Taleb, dll), mode full/quick/duo, triad, profil, verdict template | ✅ ter-install di `skills/council`, diaktifkan via `AGENTS.md` |

**Cara pakai di proyek ini (tertulis di `AGENTS.md`):**
- Ponytail = aturan default setiap menulis kode (anti over-engineering).
- Council = wajib sebelum keputusan besar rebuild (panel saran:
  `socrates,kahneman,torvalds` / `feynman,torvalds,meadows` /
  `munger,taleb,watts`).

---

## 3️⃣ PRESEDEN (app sejenis, 15+)

### Jurnal trading open-source
| Repo | ⭐ | Fitur yang bisa dicontoh |
|---|---|---|
| Eleven-Trading/TradeNote | 918 | Jurnal trading OS: import broker, dashboard, Docker+MongoDB |
| GeneBO98/tradetally | 328 | Trade tracking + analytics (alternatif TraderVue) |
| Cursivez/journalit | 213 | Obsidian plugin: local-first, CSV import, MT4/Tradovate sync |
| hugodemenez/deltalytix | 143 | Jurnal + AI agents + dashboard statistik |
| Bilovodskyi/ai-trading-journal | 70 | Kalender cantik untuk tambah/lihat trade |
| mransbro/tradingjournal | 51 | Jurnal trade simpel pakai Flask (mirip stack kita!) |

### Dashboard MT5 / trading
| Repo | ⭐ |
|---|---|
| peridotfoundation/MT5-Directional-Flow-Dashboard | 115 |
| mobilesitebytim/Forex-Trend-Dashboard-Engine | 117 |
| NadirAliOfficial/mt5-dash | 12 (Streamlit analisis MT4/MT5) |
| chrisleekr/binance-trading-bot | 5.548 (live dashboard bot) |

### Jurnal komersial (preseden fitur — dari riset web)
TradeZella, TraderSync, Tradervue, Edgewonk, Moonshot Journal, TradesViz,
Trademetria, TradeNote, JournalPlus — fitur inti: auto-sync, kalender P&L,
insight psikologi, laporan mingguan/bulanan, Zella Score, prop simulator,
kalender ekonomi, MAE/MFE, backtesting/replay.

---

## 4️⃣ STUDI KASUS (case studies)

1. **Trading app UX/UI (Medium, Vanshika Dosani)** — SWOT, persona, 60:30:10
   (60% krem, 30% hijau, 10% aksen biru), ikon familiar, dummy trading untuk
   pemula, dashboard + watchlist + edukasi.
2. **Fintech Dashboard UX (Arivan Infotech)** — dashboard institusional
   real-time: Next.js + Tailwind + WebSockets + canvas rendering.
   Hasil: layout shift 0, loading 3.5× lebih cepat, aktivitas trading +28%.
3. **VaultX AI Finance App (Medium)** — dark mode + gradien lembut +
   translusen; minimalis, kartu bersih, tipografi kontras; user testing
   dengan pengguna nyata.
4. **F6 Online Stock Trading App (Daffodil)** — UX riset ekstensif, navigasi
   mudah, watchlist personal, E-KYC, notifikasi berita, manajemen multi-akun.
   Hasil: pengguna baru +36%, transaksi harian +56%.
5. **Fundify (Figma Community)** — studi kasus fintech mobile lengkap.

---

## 5️⃣ SKILL TERKAIT (charts, ikon, data, MT5 API)

### Chart library
lightweight-charts (TradingView, sudah kita pakai), recharts (27.5k⭐),
billboard.js (6k⭐, D3), cal-heatmap (3.1k⭐ — heatmap kalender P&L!),
britecharts, plotly.js.

### Ikon & font
lucide (MIT, ikon konsisten — **pengganti emoji**), Material Symbols,
Roboto/Inter (Google Fonts).

### API MT5 (penting untuk model WEB!)
| Repo/Produk | Fungsi |
|---|---|
| **metaapi.cloud (SDK resmi)** | API cloud MT4/MT5: REST + WebSocket, bisa konek akun MT5 **tanpa terminal lokal** — solusi "web pasti" paling murni! Free tier tersedia |
| dceoy/mt5api | REST API MT5 (FastAPI + pdmt5) dengan auth API key — pola persis connector kita |
| mikha-dev/mt5-rest, DevRico003/mt5-rest-api | MT5 jadi REST server via EA (MQL5) |
| agiliumtrade-ai/metastats | API statistik trading MT4/MT5 |
| MTsocketAPI | C#/Python library MT4/MT5 |

---

## 6️⃣ SUMBER DAYA DATA (memperkaya data)

### Data historis forex (gratis)
Dukascopy (tick+bar, 15+ tahun, gratis), HistData (M1, 10+ tahun),
Tickstory, OANDA API (bar 5s–bulanan, 32 tahun), Myfxbook Historical Data,
Forexite, Yahoo Finance via yfinance (`GBPUSD=X`).

### Kalender ekonomi (untuk fitur P1)
Forex Factory calendar (gratis, scraping/API komunitas), Myfxbook economic
calendar, Trading Economics API (berbayar), investing.com calendar.

### Sumber statistik & referensi
MetaStats API, tradingview widget/lightweight-charts, GitHub topics
`trading-journal`, `mt4-api`, `mt5-api`, `ui-design`, `ui-skills`.

---

## 7️⃣ PRINSIP UX YANG DIKUMPULKAN (dipakai di ui-foundation/)

1. **WCAG 2.2 AA (POUR)** — kontras teks ≥ 4.5:1, keyboard navigation,
   focus visible, label form, alt text, semantic HTML, error jelas.
2. **10 Heuristics Nielsen** + UX audit 50 poin (navigasi, form, aksesibilitas,
   mobile, performa, konten).
3. **Dashboard principles (UXPin 2026)** — hierarki visual (KPI di kiri-atas),
   minimalkan cognitive load, progressive disclosure, drill-down/filter,
   chart sesuai jenis data, jangan andalkan warna saja (buta warna).
4. **60:30:10 rule** — 60% warna dasar, 30% sekunder, 10% aksen.
5. **Aturan plugin87 skill** — no-emoji icon, empty state kuat, loading≠disabled,
   komposisi dulu, type scale berani, satu pembeda per daftar.
6. **UX Laws** — Hick's Law (sedikit pilihan), Fitts (target besar),
   Jakob's Law (pola familiar), Zeigarnik (progress terlihat).
