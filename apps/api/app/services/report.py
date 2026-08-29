"""Laporan bulanan PDF (BLUEPRINT §25) — on-demand sinkron (MVP tanpa RQ).

Isi: ringkasan P&L · win rate · PF · drawdown · best/worst trade/hari/simbol ·
distribusi R · psikologi (emosi dominan, rule adherence) · MAE/MFE ringkas ·
performance score · equity curve (SVG) · kalender P&L.
"""
import html
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from weasyprint import HTML

from packages.analytics import calendar_days, equity_curve, performance_score, summarize
from packages.db.models import JournalEntry, MaeMfeRecord, Trade, TradingAccount

MONTHS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
DAY_NAMES = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


def _money(v, currency: str = "USD") -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:,.2f} {currency}"


def _r_bucket(r: float | None) -> str:
    if r is None:
        return "n/a"
    if r < -2:
        return "< −2R"
    if r < -1:
        return "−2…−1R"
    if r < 0:
        return "−1…0R"
    if r < 1:
        return "0…1R"
    if r < 2:
        return "1…2R"
    return "> 2R"


def _group_best(rows: list[dict], key: str, value_key: str) -> tuple[str | None, float | None]:
    groups: dict[str, float] = {}
    for t in rows:
        k = str(t.get(key) or "")
        groups[k] = groups.get(k, 0.0) + float(t.get(value_key) or 0)
    if not groups:
        return None, None
    best = max(groups.items(), key=lambda kv: kv[1])
    return best[0], best[1]


def _equity_svg(points: list[dict], width: int = 640, height: int = 150) -> str:
    """Line chart equity sederhana (SVG inline — didukung weasyprint)."""
    if len(points) < 2:
        return "<p>Belum cukup data untuk equity curve.</p>"
    values = [p["equity"] for p in points]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    pad = 10
    step_x = (width - 2 * pad) / (len(points) - 1)
    coords = [
        (pad + i * step_x, height - pad - (v - lo) / span * (height - 2 * pad))
        for i, v in enumerate(values)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    first = values[0]
    area = f"{pad},{height - pad - (first - lo) / span * (height - 2 * pad):.1f} " + line + f" {width - pad:.1f},{height - pad:.1f}"
    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;height:auto">'
        f'<polygon points="{area}" fill="rgba(34,139,230,0.12)"/>'
        f'<polyline points="{line}" fill="none" stroke="#228be6" stroke-width="2"/>'
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="#ccc" stroke-width="1"/>'
        f"</svg>"
    )


def build_monthly_report(db: Session, account: TradingAccount, month: str) -> bytes:
    """PDF laporan bulan `month` (YYYY-MM). Tenant-safe oleh caller."""
    year, m = int(month[:4]), int(month[5:7])
    start = datetime(year, m, 1)
    end = datetime(year + 1, 1, 1) if m == 12 else datetime(year, m + 1, 1)
    cur = account.currency or "USD"

    trades = db.scalars(
        select(Trade).where(
            Trade.trading_account_id == account.id,
            Trade.deleted_at.is_(None),
            Trade.close_time >= start,
            Trade.close_time < end,
        )
    ).all()
    rows = [
        {
            "net_profit": float(t.net_profit or 0), "gross_profit": float(t.gross_profit or 0),
            "r_multiple": float(t.r_multiple) if t.r_multiple is not None else None,
            "open_time": t.open_time, "close_time": t.close_time,
            "symbol": t.symbol, "side": t.side, "ticket": t.ticket,
            "day": t.close_time.strftime("%Y-%m-%d") if t.close_time else "",
        }
        for t in trades
    ]
    s = summarize(rows)

    # equity curve & kalender bulan ini
    eq_points = equity_curve(rows)
    cal = calendar_days(rows, month=month)

    # best/worst
    best_trade = max(rows, key=lambda t: t["net_profit"]) if rows else None
    worst_trade = min(rows, key=lambda t: t["net_profit"]) if rows else None
    best_day, best_day_pnl = _group_best(rows, "day", "net_profit")
    best_sym, best_sym_pnl = _group_best(rows, "symbol", "net_profit")
    worst_sym, worst_sym_pnl = _group_best(rows, "symbol", "net_profit")

    # distribusi R
    r_dist: dict[str, int] = {}
    for t in rows:
        b = _r_bucket(t["r_multiple"])
        r_dist[b] = r_dist.get(b, 0) + 1
    r_buckets = ["< −2R", "−2…−1R", "−1…0R", "0…1R", "1…2R", "> 2R"]

    # psikologi: jurnal bulan ini
    entries = db.scalars(
        select(JournalEntry).where(
            JournalEntry.trading_account_id == account.id,
            JournalEntry.entry_date >= start,
            JournalEntry.entry_date < end,
        )
    ).all()
    emotion_counts: dict[str, int] = {}
    adherence_rows = 0
    adherence_true = 0
    for e in entries:
        emo = e.emotion_during or "—"
        emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
        if e.rule_adherence is not None:
            adherence_rows += 1
            adherence_true += 1 if e.rule_adherence else 0
    dominant_emotion = max(emotion_counts.items(), key=lambda kv: kv[1]) if emotion_counts else None
    adherence_pct = (adherence_true / adherence_rows * 100) if adherence_rows else None

    # MAE/MFE ringkas (trade bulan ini)
    recs = db.execute(
        select(MaeMfeRecord, Trade)
        .join(Trade, MaeMfeRecord.trade_id == Trade.id)
        .where(MaeMfeRecord.trading_account_id == account.id, Trade.close_time >= start, Trade.close_time < end)
    ).all()
    mae_pcts = [float(r.mae_pct) for r, _ in recs if r.mae_pct is not None]
    mfe_pcts = [float(r.mfe_pct) for r, _ in recs if r.mfe_pct is not None]

    # performance score (semua trade akun)
    all_rows = [
        {
            "net_profit": float(t.net_profit or 0), "gross_profit": float(t.gross_profit or 0),
            "r_multiple": float(t.r_multiple) if t.r_multiple is not None else None,
            "open_time": t.open_time, "close_time": t.close_time,
        }
        for t in db.scalars(
            select(Trade).where(
                Trade.trading_account_id == account.id, Trade.deleted_at.is_(None)
            )
        ).all()
    ]
    all_journal_count = db.query(JournalEntry).filter(
        JournalEntry.trading_account_id == account.id
    ).count()
    score = performance_score(all_rows, journal_count=all_journal_count)

    mae_avg = f"{sum(mae_pcts) / len(mae_pcts):.3f}%" if mae_pcts else "—"
    mfe_avg = f"{sum(mfe_pcts) / len(mfe_pcts):.3f}%" if mfe_pcts else "—"
    dur = s["avg_duration_min"]
    dur_str = f"{dur / 60:.1f} jam" if dur is not None else "—"
    emotion_html = (
        f"{html.escape(dominant_emotion[0])} <small>({dominant_emotion[1]} jurnal)</small>"
        if dominant_emotion else "—"
    )
    month_label = f"{MONTHS_ID[m - 1]} {year}"
    n = s["total_trades"]
    no_data = n == 0
    wr = s["win_rate"] if s["win_rate"] is not None else 0.0
    pf = s["profit_factor"]
    pf_str = f"{pf:.2f}" if pf is not None else "—"
    dd = s["max_drawdown"] or 0.0
    exp = s["expectancy"] or 0.0

    # kalender grid (7 kolom, Senin pertama)
    cal_map = {c["day"]: c for c in cal}
    first = datetime(year, m, 1)
    first_weekday = (first.weekday() + 1) % 7  # Sen=0 → 0..6, Minggu=6
    cells: list[tuple[str, float | None, int]] = []
    day_cursor = first
    for _ in range(first_weekday):
        cells.append(("", None, 0))
    while day_cursor.month == m:
        key = day_cursor.strftime("%Y-%m-%d")
        c = cal_map.get(key)
        cells.append((day_cursor.day, c["net_profit"] if c else None, c["trades"] if c else 0))
        day_cursor = day_cursor + timedelta(days=1)
    while len(cells) % 7 != 0:
        cells.append(("", None, 0))

    cal_rows_html = []
    for i in range(0, len(cells), 7):
        tds = []
        for day, pnl, _cnt in cells[i : i + 7]:
            cls = ""
            if pnl is not None:
                cls = "pos" if pnl > 0 else ("neg" if pnl < 0 else "flat")
            label = f"{day}" if day else ""
            sub = f"{pnl:+,.0f}" if pnl is not None else ""
            tds.append(f'<td class="{cls}">{label}{"<br><small>" + sub + "</small>" if sub else ""}</td>')
        cal_rows_html.append("<tr>" + "".join(tds) + "</tr>")

    score_html = ""
    if score.get("score") is not None:
        comps = " · ".join(
            f"{k.replace('_', ' ')} {round(v['sub'] * 100)}" for k, v in score["components"].items()
        )
        score_html = (
            f'<tr><th>Skor Performa</th><td><b>{score["score"]} — {score["label"]}</b>'
            f'<br><small>{comps}</small></td></tr>'
        )

    html_str = f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 14mm 12mm; }}
body {{ font-family: 'DejaVu Sans', sans-serif; font-size: 10px; color: #1a1f26; }}
h1 {{ font-size: 17px; margin: 0 0 2px; }} h2 {{ font-size: 12px; margin: 14px 0 5px; border-bottom: 1px solid #dde; padding-bottom: 2px; }}
.sub {{ color: #667; font-size: 9.5px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 4px; }}
th, td {{ border: 1px solid #dde; padding: 3px 6px; text-align: left; }}
th {{ background: #f2f5f9; font-weight: bold; }}
.pos {{ color: #0a7a33; }} .neg {{ color: #c92a2a; }} .flat {{ color: #888; }}
.kpis {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
.kpi {{ border: 1px solid #dde; border-radius: 6px; padding: 6px 10px; min-width: 110px; }}
.kpi b {{ display: block; font-size: 13px; }} .kpi span {{ color: #667; font-size: 9px; }}
small {{ color: #667; }}
</style></head><body>
<h1>Laporan Bulanan — {html.escape(account.name)}</h1>
<div class="sub">{month_label} · Akun {html.escape(account.login or '')} ({html.escape(account.server or '')}) · Mata uang {cur} · Dibuat {datetime.now().strftime('%d %B %Y %H:%M')}</div>

<div class="kpis">
  <div class="kpi"><span>P&L Bersih</span><b class="{'pos' if s['net_profit'] >= 0 else 'neg'}">{_money(s["net_profit"], cur)}</b></div>
  <div class="kpi"><span>Trade</span><b>{n}</b></div>
  <div class="kpi"><span>Win Rate</span><b>{wr:.1f}%</b></div>
  <div class="kpi"><span>Profit Factor</span><b>{pf_str}</b></div>
  <div class="kpi"><span>Max Drawdown</span><b class="neg">{_money(dd, cur)}</b></div>
  <div class="kpi"><span>Expectancy</span><b class="{'pos' if exp >= 0 else 'neg'}">{_money(exp, cur)}</b></div>
</div>

<h2>Ringkasan</h2>
<table>
<tr><th>Metrik</th><th>Nilai</th><th>Metrik</th><th>Nilai</th></tr>
<tr><td>Trade menang</td><td class="pos">{s["win_count"]}</td><td>Trade kalah</td><td class="neg">{s["loss_count"]}</td></tr>
<tr><td>Gross profit</td><td class="pos">{_money(s["gross_profit"], cur)}</td><td>Gross loss</td><td class="neg">{_money(-s["gross_loss"], cur)}</td></tr>
<tr><td>Best trade</td><td class="pos">{_money(best_trade["net_profit"], cur) if best_trade else "—"} <small>{html.escape(best_trade["symbol"]) if best_trade else ""}</small></td>
<td>Worst trade</td><td class="neg">{_money(worst_trade["net_profit"], cur) if worst_trade else "—"} <small>{html.escape(worst_trade["symbol"]) if worst_trade else ""}</small></td></tr>
<tr><td>Simbol terbaik</td><td class="pos">{html.escape(str(best_sym)) if best_sym else "—"} {_money(best_sym_pnl, cur) if best_sym_pnl is not None else ""}</td>
<td>Simbol terburuk</td><td class="neg">{html.escape(str(worst_sym)) if worst_sym else "—"} {_money(worst_sym_pnl, cur) if worst_sym_pnl is not None else ""}</td></tr>
<tr><td>Hari terbaik</td><td class="pos">{best_day or "—"} {_money(best_day_pnl, cur) if best_day_pnl is not None else ""}</td>
<td>Avg durasi</td><td>{dur_str}</td></tr>
<tr><td>MAE rata-rata</td><td class="neg">{mae_avg} <small>({len(mae_pcts)} trade)</small></td>
<td>MFE rata-rata</td><td class="pos">{mfe_avg}</td></tr>
{score_html}
</table>

<h2>Equity Curve — {month_label}</h2>
{_equity_svg(eq_points)}

<h2>Kalender P&L — {month_label}</h2>
<table><tr>{"".join(f"<th>{d}</th>" for d in DAY_NAMES)}</tr>{''.join(cal_rows_html)}</table>

<h2>Distribusi R</h2>
<table><tr>{"".join(f"<th>{b}</th>" for b in r_buckets)}</tr>
<tr>{"".join(f'<td>{r_dist.get(b, 0)}</td>' for b in r_buckets)}</tr></table>

<h2>Psikologi — {month_label}</h2>
<table>
<tr><th>Emosi dominan saat trading</th><td>{emotion_html}</td></tr>
<tr><th>Rule adherence</th><td>{f"{adherence_pct:.0f}% patuh" if adherence_pct is not None else "—"}</td></tr>
<tr><th>Jurnal bulan ini</th><td>{len(entries)} entri</td></tr>
</table>
{('<p class="sub">Tidak ada trade pada bulan ini — laporan kosong.</p>' if no_data else "")}
</body></html>"""

    return HTML(string=html_str).write_pdf()
