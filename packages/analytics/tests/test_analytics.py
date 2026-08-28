"""Test unit packages/analytics — formula metrik (BLUEPRINT §12)."""
from datetime import UTC, datetime, timedelta

from packages.analytics import calendar_days, equity_curve, monthly_summary, summarize


def _t(net, day_offset=1, r=1.0, **kw):
    now = datetime.now(UTC)
    return {
        "net_profit": net,
        "gross_profit": net if net > 0 else 0,
        "open_time": now - timedelta(days=day_offset, hours=2),
        "close_time": now - timedelta(days=day_offset),
        "r_multiple": r,
        **kw,
    }


def test_summarize_empty():
    s = summarize([])
    assert s["total_trades"] == 0
    assert s["win_rate"] is None and s["profit_factor"] is None
    assert s["net_profit"] == 0.0


def test_summarize_basic():
    trades = [_t(100), _t(-40), _t(60), _t(0), _t(30)]
    s = summarize(trades)
    assert s["total_trades"] == 5
    assert s["win_count"] == 3 and s["loss_count"] == 1 and s["be_count"] == 1
    assert s["net_profit"] == 150.0
    assert s["gross_profit"] == 190.0 and s["gross_loss"] == 40.0
    # win rate: breakeven tidak dihitung → 3/4 = 75%
    assert s["win_rate"] == 75.0
    assert s["profit_factor"] == 4.75
    assert s["best_trade"] == 100.0 and s["worst_trade"] == -40.0
    assert s["winning_streak"] == 2 and s["losing_streak"] == 1


def test_summarize_zero_loss_profit_factor_infinite():
    s = summarize([_t(50), _t(20)])
    assert s["profit_factor"] == 999.0  # tak terdefinisi → 999 (konvensi blueprint)
    assert s["win_rate"] == 100.0


def test_summarize_max_drawdown():
    # +100 lalu -50 → drawdown 50 dari peak 100
    trades = [_t(100, day_offset=2), _t(-50, day_offset=1)]
    s = summarize(trades)
    assert s["max_drawdown"] == 50.0
    assert s["net_profit"] == 50.0


def test_calendar_days_grouping():
    trades = [_t(10, day_offset=1), _t(-5, day_offset=1), _t(7, day_offset=3)]
    days = calendar_days(trades)
    assert len(days) == 2
    # urut ascending: hari 3 hari lalu (7.0) dulu, lalu kemarin (5.0)
    assert days[0]["net_profit"] == 7.0 and days[0]["trades"] == 1
    assert days[1]["net_profit"] == 5.0 and days[1]["trades"] == 2 and days[1]["wins"] == 1


def test_calendar_days_month_filter():
    trades = [_t(10, day_offset=1), _t(7, day_offset=400)]  # kedua di bulan beda
    current = datetime.now(UTC).date().isoformat()[:7]
    days = calendar_days(trades, current)
    assert all(d["day"][:7] == current for d in days)


def test_equity_curve_cumulative():
    trades = [_t(100, day_offset=2), _t(-30, day_offset=1)]
    curve = equity_curve(trades)
    assert [p["equity"] for p in curve] == [100.0, 70.0]
    assert curve[0]["ts"] < curve[1]["ts"]


def test_monthly_summary_groups():
    trades = [_t(10, day_offset=1), _t(20, day_offset=40)]
    months = monthly_summary(trades)
    assert len(months) == 2
    assert months[0]["total_trades"] == 1
