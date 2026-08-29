"""Phase 5 — Analitik trading murni (reuse pola journal_math.py, tanpa UI).

Semua fungsi murni (pure) atas list dict trade — mudah diuji, dipakai API.
Metrik mengikuti BLUEPRINT §12 (21 metrik; subset inti di sini).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from statistics import mean

# ---------------------------------------------------------------- ringkas


def _normalize_trades(trades: list[dict]) -> list[dict]:
    """Decimal → float (SQLAlchemy Numeric bisa kirim Decimal)."""
    return [
        {**t, "net_profit": float(t.get("net_profit") or 0),
         "gross_profit": float(t.get("gross_profit") or t.get("net_profit") or 0),
         "r_multiple": float(t["r_multiple"]) if t.get("r_multiple") is not None else None}
        for t in trades
    ]


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
    trades = _normalize_trades(trades)
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
    if isinstance(v, int | float):
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


# ---------------------------------------------------------------- performance score


def _sigmoid(x: float, k: float = 2.0) -> float:
    return 1.0 / (1.0 + math.exp(-k * x))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def performance_score(
    trades: list[dict],
    *,
    plan_match_rate: float | None = None,
    rule_adherence_rate: float | None = None,
    revenge_ratio: float | None = None,
    emotion_stability: float | None = None,
    journal_count: int = 0,
) -> dict:
    """Skor performa 0–100 (BLUEPRINT §13).

    Komponen: Risk 20 · Consistency 20 · Profitability 20 · Drawdown 15 ·
    Trade Quality 15 · Discipline 10 (diprorata bila jurnal < 10 entri).
    Data kurang dari 20 trade → skor None + progress (tidak menebak).
    """
    trades = _normalize_trades(trades)
    s = summarize(trades)
    n = s["total_trades"]
    need = 20
    if n < need:
        return {"score": None, "progress": n, "need": need, "label": None}

    # --- Risk Management (20): avg_loss vs 1R; 1R = avg_loss / avg|r_loss|
    r_losses = [abs(t.get("r_multiple") or 0) for t in trades if (t.get("net_profit") or 0) < 0 and t.get("r_multiple")]
    avg_r_loss = mean(r_losses) if r_losses else 1.0
    risk_mgmt = _clamp01(1.0 - min(1.0, avg_r_loss))

    # --- Consistency (20): sigmoid atas koefisien variasi R
    rs = [t.get("r_multiple") for t in trades if t.get("r_multiple") is not None]
    if len(rs) >= max(3, n // 2):
        mean_r = abs(mean(rs))
        std_r = (sum((r - mean(rs)) ** 2 for r in rs) / len(rs)) ** 0.5
        cv = (std_r / mean_r) if mean_r > 1e-9 else 0.0
    else:  # fallback: net_profit per trade
        nets = [t.get("net_profit") or 0 for t in trades]
        m = mean(nets)
        std = (sum((v - m) ** 2 for v in nets) / len(nets)) ** 0.5
        cv = (std / abs(m)) if abs(m) > 1e-9 else 0.0
    consistency = _sigmoid(1.0 - cv)

    # --- Profitability (20): sigmoid(expectancy_R/0.5)*0.6 + sigmoid(PF/2)*0.4
    exp_r = mean([t.get("r_multiple") or 0 for t in trades]) if rs else (
        s["expectancy"] or 0) / max(abs(s["avg_loss"] or 0), 1e-9)
    pf = s["profit_factor"] if s["profit_factor"] is not None else 0.0
    profitability = _sigmoid(exp_r / 0.5) * 0.6 + _sigmoid(pf / 2.0) * 0.4

    # --- Drawdown Control (15): max_dd relatif peak equity curve
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for t in sorted(trades, key=lambda x: x.get("close_time") or 0):
        equity += t.get("net_profit") or 0
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    dd_pct = max_dd / max(1e-9, peak)
    dd_control = _clamp01(1.0 - min(1.0, dd_pct / 0.20))
    if dd_pct < 0.10:
        dd_control = min(1.0, dd_control + 0.10)

    # --- Trade Quality (15): 0.5×(1−MAE/MFE) + 0.25×plan_match + 0.25×RR_norm
    maes = [abs(t.get("mae") or 0) for t in trades if t.get("mae") is not None]
    mfes = [abs(t.get("mfe") or 0) for t in trades if t.get("mfe") is not None]
    if maes and mfes:
        ratio = min(1.0, (sum(maes) / len(maes)) / max(1e-9, sum(mfes) / len(mfes)))
        mae_sub = 1.0 - ratio
    else:
        mae_sub = 0.5  # tanpa data MAE/MFE → netral (bukan hukuman)
    plan_sub = _clamp01(plan_match_rate) if plan_match_rate is not None else 0.5
    rr = (s["avg_win"] or 0) / max(abs(s["avg_loss"] or 0), 1e-9)
    rr_sub = _clamp01(rr / 2.0)
    trade_quality = _clamp01(0.5 * mae_sub + 0.25 * plan_sub + 0.25 * rr_sub)

    components = {
        "risk_mgmt": (20, risk_mgmt),
        "consistency": (20, consistency),
        "profitability": (20, profitability),
        "drawdown": (15, dd_control),
        "trade_quality": (15, trade_quality),
    }

    # --- Discipline (10): hanya bila jurnal cukup; selainnya diprorata (penalti data)
    data_complete = journal_count >= 10
    if data_complete:
        adherence = _clamp01(rule_adherence_rate) if rule_adherence_rate is not None else 0.5
        no_revenge = 1.0 - _clamp01(revenge_ratio) if revenge_ratio is not None else 0.5
        stability = _clamp01(emotion_stability) if emotion_stability is not None else 0.5
        components["discipline"] = (10, _clamp01(0.5 * adherence + 0.3 * no_revenge + 0.2 * stability))
    else:  # prorata bobot 10 ke 5 komponen lain (+2 tiap komponen)
        components = {k: (w + 2, sub) for k, (w, sub) in components.items()}

    score = round(sum(w * sub for w, sub in components.values()))

    label = (
        "Excellent" if score >= 85 else "Strong" if score >= 70 else
        "Good" if score >= 55 else "Needs Improvement" if score >= 40 else "Poor"
    )
    return {
        "score": score,
        "progress": n,
        "need": need,
        "label": label,
        "data_complete": data_complete,
        "components": {k: {"weight": w, "sub": round(sub, 3)} for k, (w, sub) in components.items()},
    }
