"""Phase 5 — Analitik trading murni (reuse pola journal_math.py, tanpa UI).

Semua fungsi murni (pure) atas list dict trade — mudah diuji, dipakai API.
Metrik mengikuti BLUEPRINT §12 (21 metrik; subset inti di sini).
"""
from __future__ import annotations

import math
from datetime import UTC, date, datetime, time, timezone
from statistics import mean

# ---------------------------------------------------------------- ringkas


def summarize(trades: list[dict]) -> dict:
    """KPI inti dari daftar trade (dict: net_profit, gross_profit, dll).

    Semua metrik nol-aman: akun kosong → metrik None/0 tanpa error.
    """
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0, "win_count": 0, "loss_count": 0, "be_count": 0,
            "net_profit": 0.0, "gross_profit": 0.0, "gross_loss": 0.0,
            "win_rate": None, "profit_factor": None, "expectancy": None,
            "avg_win": None, "avg_loss": None, "best_trade": None,
            "worst_trade": None, "r_sum": 0.0, "max_drawdown": None,
            "winning_streak": 0, "losing_streak": 0, "avg_duration_min": None,
        }
    wins = [t for t in trades if (t.get("net_profit") or 0) > 0]
    losses = [t for t in trades if (t.get("net_profit") or 0) < 0]
    be = [t for t in trades if (t.get("net_profit") or 0) == 0]
    gross_profit = sum(t.get("gross_profit") or t.get("net_profit") or 0 for t in wins)
    gross_loss = abs(sum(t.get("net_profit") or 0 for t in losses))
    net = sum(t.get("net_profit") or 0 for t in trades)
    r_total = sum(t.get("r_multiple") or 0 for t in trades)

    decided = wins + losses  # breakeven tidak dihitung dalam win rate
    win_rate = (len(wins) / len(decided)) if decided else None
    profit_factor = (gross_profit / gross_loss) if gross_loss else (None if gross_profit == 0 else 999.0)
    avg_win = mean(t.get("net_profit") or 0 for t in wins) if wins else None
    avg_loss = mean(t.get("net_profit") or 0 for t in losses) if losses else None
    expectancy = (net / n) if n else None
    best = max(t.get("net_profit") or 0 for t in trades)
    worst = min(t.get("net_profit") or 0 for t in trades)

    # drawdown dari equity curve kumulatif
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for t in sorted(trades, key=lambda x: x.get("close_time") or 0):
        equity += t.get("net_profit") or 0
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    win_streak = loss_streak = cur_win = cur_loss = 0
    for t in sorted(trades, key=lambda x: x.get("close_time") or 0):
        if (t.get("net_profit") or 0) > 0:
            cur_win += 1
            cur_loss = 0
        elif (t.get("net_profit") or 0) < 0:
            cur_loss += 1
            cur_win = 0
        win_streak = max(win_streak, cur_win)
        loss_streak = max(loss_streak, cur_loss)

    durations = []
    for t in trades:
        o, c = t.get("open_time"), t.get("close_time")
        if o and c:
            try:
                durations.append((_dt(c) - _dt(o)).total_seconds() / 60)
            except (TypeError, ValueError):
                continue
    return {
        "total_trades": n, "win_count": len(wins), "loss_count": len(losses),
        "be_count": len(be), "net_profit": round(net, 2),
        "gross_profit": round(gross_profit, 2), "gross_loss": round(gross_loss, 2),
        "win_rate": round(win_rate * 100, 1) if win_rate is not None else None,
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "expectancy": round(expectancy, 2) if expectancy is not None else None,
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "best_trade": round(best, 2), "worst_trade": round(worst, 2),
        "r_sum": round(r_total, 2),
        "max_drawdown": round(max_dd, 2),
        "winning_streak": win_streak, "losing_streak": loss_streak,
        "avg_duration_min": round(mean(durations), 1) if durations else None,
    }


def _dt(v) -> datetime:
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=UTC)
    return datetime.fromisoformat(str(v))


def calendar_days(trades: list[dict], month: str | None = None) -> list[dict]:
    """P&L per hari — untuk kalender heatmap (BLUEPRINT §17).

    month: "YYYY-MM" (UTC); None → semua hari.
    """
    per_day: dict[str, dict] = {}
    for t in trades:
        try:
            day = _dt(t.get("close_time") or 0).date()
        except (TypeError, ValueError):
            continue
        if month and day.isoformat()[:7] != month:
            continue
        net = t.get("net_profit") or 0
        entry = per_day.setdefault(
            day.isoformat(), {"day": day.isoformat(), "net_profit": 0.0, "trades": 0, "wins": 0}
        )
        entry["net_profit"] += net
        entry["trades"] += 1
        if net > 0:
            entry["wins"] += 1
    return [per_day[k] for k in sorted(per_day)]


def equity_curve(trades: list[dict]) -> list[dict]:
    """P&L kumulatif per trade — fallback bila equity_snapshots kosong."""
    equity = 0.0
    points = []
    for t in sorted(trades, key=lambda x: x.get("close_time") or 0):
        equity += t.get("net_profit") or 0
        points.append(
            {"ts": _dt(t.get("close_time") or 0).isoformat(), "equity": round(equity, 2)}
        )
    return points


def monthly_summary(trades: list[dict]) -> list[dict]:
    """Ringkasan per bulan (untuk tabel Laporan)."""
    groups: dict[str, list[dict]] = {}
    for t in trades:
        try:
            month = _dt(t.get("close_time") or 0).date().isoformat()[:7]
        except (TypeError, ValueError):
            continue
        groups.setdefault(month, []).append(t)
    out = []
    for month, rows in sorted(groups.items()):
        s = summarize(rows)
        out.append({"month": month, **s})
    return out
