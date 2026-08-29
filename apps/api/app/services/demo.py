"""Generator akun demo sintetis "Data Contoh" (KEPUTUSAN-FINAL DR-03).

Menghasilkan akun + 60–90 hari trading realistis:
- 120–220 trades tertutup (win rate 45–55%, R loss −0.8..−2.2, win +0.5..+3.0)
- deals (entry+exit), 1–3 posisi terbuka
- equity & balance snapshot harian, deposit/withdrawal
- daily & monthly statistics
- 6–10 jurnal + tag + psikologi
Semua data random dengan seed per akun → deterministik, <5 detik.
"""
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from packages.db.models import (
    BalanceSnapshot,
    DailyStatistic,
    Deal,
    Deposit,
    EquitySnapshot,
    JournalEntry,
    MaeMfeRecord,
    MonthlyStatistic,
    Position,
    PsychologyEntry,
    Tag,
    Trade,
    TradingAccount,
    Withdrawal,
    trade_tags,
)

# (simbol, bobot)
SYMBOLS = [
    ("EURUSD", 25), ("GBPUSD", 15), ("USDJPY", 12), ("XAUUSD", 20),
    ("BTCUSD", 8), ("US30", 12), ("NAS100", 8),
]
BASE_PRICES = {
    "EURUSD": 1.0823, "GBPUSD": 1.2611, "USDJPY": 155.40, "XAUUSD": 2401.5,
    "BTCUSD": 65300.0, "US30": 38950.0, "NAS100": 18480.0,
}
SETUPS = ["Breakout", "Retest", "News", "Trend", "Reversal"]
EMOTIONS = ["calm", "confident", "anxious", "greedy", "fearful", "neutral", "frustrated"]
NOTES_ID = [
    "Entry sesuai plan, menunggu konfirmasi candle.",
    "Lepas lebih awal karena ragu, padahal arah sudah benar.",
    "Menunggu retest level, entry setelah konfirmasi.",
    "Disiplin mengikuti rencana, exit di TP.",
    "Sedikit FOMO, entry telat dari breakout.",
    "Manajemen risiko rapi, cut loss cepat.",
    "Sesi London, momentum bagus, mengikuti trend.",
    "Koreksi ke support, entry reversal dengan SL ketat.",
]
TAG_NAMES = ["breakout", "retest", "news", "plan", "harian"]

_TZ = UTC


def _symbol_pool(rng: random.Random) -> str:
    return rng.choices([s for s, _ in SYMBOLS], weights=[w for _, w in SYMBOLS])[0]


def generate_demo_account(db: Session, user_id: int, name: str = "Data Contoh") -> TradingAccount:
    """Buat akun demo + seluruh data sintetis. Caller wajib db.commit()."""
    rng = random.Random()
    account = TradingAccount(
        user_id=user_id,
        name=name,
        login=f"DEMO-{rng.randint(100000, 999999)}",
        server="Synthetic",
        kind="demo",
        currency="USD",
        leverage=100,
        broker_tz=120,  # UTC+2 (EET — pola HF Markets demo)
        hf_preset=False,
        is_active=True,
    )
    db.add(account)
    db.flush()  # dapat account.id

    seed = rng.randint(1, 10**9)
    rng = random.Random(seed)  # deterministik per akun

    today = datetime.now(_TZ).date()
    span = rng.randint(60, 90)
    start = today - timedelta(days=span)
    trading_days = [
        start + timedelta(days=i)
        for i in range((today - start).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    ]

    # distribusi trades per hari (0–4)
    n_trades = rng.randint(120, 220)
    day_counts = [0] * len(trading_days)
    for _ in range(n_trades):
        day_counts[rng.randrange(len(trading_days))] += 1

    win_prob = rng.uniform(0.45, 0.55)
    ticket = rng.randint(100000, 999999)
    deal_ticket = ticket + 1000000

    # narasi dana
    balance = 10000.0
    db.add(Deposit(user_id=user_id, trading_account_id=account.id, ts=_dt(start, 8, 0),
                   amount=10000.0, method="bank", note="Deposit awal"))
    mid_idx = len(trading_days) // 2
    db.add(Deposit(user_id=user_id, trading_account_id=account.id, ts=_dt(trading_days[mid_idx], 8, 0),
                   amount=5000.0, method="bank", note="Tambah modal"))
    if rng.random() < 0.7:
        db.add(Withdrawal(user_id=user_id, trading_account_id=account.id,
                          ts=_dt(trading_days[-min(15, len(trading_days))], 9, 0),
                          amount=1200.0, method="bank", note="Penarikan rutin"))

    pnl_accum = 0.0
    peak = balance
    trades_flat: list[Trade] = []
    journal_candidates: list[tuple[Trade, str]] = []
    excursion_records: list[tuple[Trade, dict]] = []

    for day, count in zip(trading_days, day_counts, strict=False):
        day_trades: list[Trade] = []
        for _ in range(count):
            symbol = _symbol_pool(rng)
            side = rng.choice(["buy", "sell"])
            volume = rng.choice([0.01, 0.02, 0.05, 0.10, 0.20, 0.50])
            risk = rng.uniform(15.0, 90.0)
            is_win = rng.random() < win_prob
            r = rng.uniform(0.5, 3.0) if is_win else -rng.uniform(0.8, 2.2)
            profit = r * risk
            swap = round(rng.uniform(-2.5, 3.0), 2) if rng.random() < 0.6 else 0.0
            commission = -round(volume * rng.uniform(2.0, 4.5), 2)
            net = profit + swap + commission

            open_time = _dt(day, rng.randint(6, 19), rng.randint(0, 59))
            close_time = open_time + timedelta(minutes=rng.randint(10, 420))

            open_price = BASE_PRICES[symbol] * (1 + rng.uniform(-0.002, 0.002))
            move = profit / max(volume * 1000.0, 1e-9)  # skala harga konsisten dgn profit
            close_price = open_price + move if side == "buy" else open_price - move
            if close_price <= 0:
                close_price = open_price

            mae_r = -abs(r) * rng.uniform(0.3, 1.0)  # negatif (R)
            mfe_r = abs(r) * rng.uniform(0.9, 1.6)
            mae_currency = mae_r * risk
            mfe_currency = mfe_r * risk
            # pct & pts langsung dari % harga wajar (bukan turunan profit — skala
            # lot×profit ke harga tidak realistis untuk lot kecil); currency tetap
            # dari R agar konsisten dengan risk_amount
            mae_pct = rng.uniform(0.05, 0.9)
            mfe_pct = mae_pct * rng.uniform(1.5, 3.5)
            mae_pts = open_price * mae_pct / 100.0
            mfe_pts = open_price * mfe_pct / 100.0
            # sumber path MAE/MFE: mayoritas ticks (connector), sisanya candles/none
            src_roll = rng.random()
            path_source = "ticks" if src_roll < 0.82 else ("candles" if src_roll < 0.91 else "none")
            samples = (
                rng.randint(20, 500) if path_source == "ticks"
                else rng.randint(5, 20) if path_source == "candles" else 0
            )

            trade = Trade(
                user_id=user_id, trading_account_id=account.id, ticket=str(ticket),
                symbol=symbol, side=side, volume=volume,
                open_price=open_price, close_price=close_price,
                open_time=open_time, close_time=close_time,
                net_profit=net, gross_profit=profit, swap=swap, commission=commission,
                mae=mae_currency, mfe=mfe_currency,
                mae_pct=mae_pct, mfe_pct=mfe_pct,
                r_multiple=r, risk_amount=risk, source="sync",
            )
            db.add(trade)
            excursion_records.append((trade, dict(
                mae_pts=mae_pts, mfe_pts=mfe_pts,
                mae_currency=mae_currency, mfe_currency=mfe_currency,
                mae_pct=mae_pct, mfe_pct=mfe_pct,
                mae_r=abs(mae_r), mfe_r=abs(mfe_r),
                path_source=path_source, samples=samples,
            )))
            db.add(Deal(user_id=user_id, trading_account_id=account.id, deal_ticket=str(deal_ticket),
                        order_ticket=str(ticket), time=open_time, type=0 if side == "buy" else 1,
                        symbol=symbol, volume=volume, price=open_price, profit=0.0,
                        comment="entry (demo)"))
            db.add(Deal(user_id=user_id, trading_account_id=account.id, deal_ticket=str(deal_ticket + 1),
                        order_ticket=str(ticket), time=close_time,
                        type=2 if side == "buy" else 3,
                        symbol=symbol, volume=volume, price=close_price, profit=profit,
                        swap=swap, commission=commission, comment="exit (demo)"))
            ticket += 1
            deal_ticket += 2
            day_trades.append(trade)
            trades_flat.append(trade)
            if rng.random() < 0.45:  # ~45% trade punya jurnal
                journal_candidates.append((trade, symbol))

        # statistik harian
        wins = [t for t in day_trades if t.net_profit > 0]
        losses = [t for t in day_trades if t.net_profit < 0]
        be = [t for t in day_trades if t.net_profit == 0]
        gp = sum(t.gross_profit for t in wins)
        gl = -sum(t.net_profit for t in losses)
        net = sum(t.net_profit for t in day_trades)
        pnl_accum += net
        balance += net
        peak = max(peak, balance)
        dd = (peak - balance) / peak if peak else 0.0
        if day_trades:
            db.add(DailyStatistic(
                user_id=user_id, trading_account_id=account.id, day=day,
                total_trades=len(day_trades), win_count=len(wins), loss_count=len(losses),
                be_count=len(be), net_profit=net, gross_profit=gp, gross_loss=gl,
                win_rate=(len(wins) / len(day_trades)) if day_trades else None,
                profit_factor=(gp / gl) if gl else (None if gp == 0 else 999.0),
                max_drawdown=dd, expectancy=(net / len(day_trades)) if day_trades else None,
                best_trade=max((t.net_profit for t in day_trades), default=None),
                worst_trade=min((t.net_profit for t in day_trades), default=None),
                avg_win=(sum(t.net_profit for t in wins) / len(wins)) if wins else None,
                avg_loss=(sum(t.net_profit for t in losses) / len(losses)) if losses else None,
                r_sum=sum(t.r_multiple or 0 for t in day_trades),
            ))
        # snapshot harian (17:00 UTC)
        db.add(EquitySnapshot(user_id=user_id, trading_account_id=account.id, ts=_dt(day, 17, 0), value=balance))
        db.add(BalanceSnapshot(user_id=user_id, trading_account_id=account.id, ts=_dt(day, 17, 0), value=balance))

    # statistik bulanan
    for month_start, month_trades in _group_by_month(trades_flat):
        wins = [t for t in month_trades if t.net_profit > 0]
        losses = [t for t in month_trades if t.net_profit < 0]
        gp = sum(t.gross_profit for t in wins)
        gl = -sum(t.net_profit for t in losses)
        net = sum(t.net_profit for t in month_trades)
        db.add(MonthlyStatistic(
            user_id=user_id, trading_account_id=account.id, month=month_start,
            total_trades=len(month_trades), win_count=len(wins), loss_count=len(losses),
            net_profit=net, gross_profit=gp, gross_loss=gl,
            win_rate=(len(wins) / len(month_trades)) if month_trades else None,
            profit_factor=(gp / gl) if gl else (None if gp == 0 else 999.0),
        ))

    # posisi terbuka 1–3
    open_now = datetime.now(_TZ)
    for _ in range(rng.randint(1, 3)):
        symbol = _symbol_pool(rng)
        side = rng.choice(["buy", "sell"])
        volume = rng.choice([0.05, 0.10, 0.20])
        price = BASE_PRICES[symbol] * (1 + rng.uniform(-0.002, 0.002))
        db.add(Position(
            user_id=user_id, trading_account_id=account.id, ticket=str(ticket), symbol=symbol,
            side=side, volume=volume, open_price=price,
            open_time=open_now - timedelta(hours=rng.randint(1, 8)),
            current_price=price * (1 + rng.uniform(-0.001, 0.001)),
            floating_pnl=rng.uniform(-40, 60), sl=None, tp=None,
        ))
        ticket += 1

    # jurnal + tag + psikologi
    db.flush()  # pastikan semua trade.id tersedia untuk MaeMfeRecord
    for trade, ex in excursion_records:
        db.add(MaeMfeRecord(
            user_id=user_id, trading_account_id=account.id, trade_id=trade.id, **ex
        ))
    db.flush()

    for trade, symbol in journal_candidates[: rng.randint(6, 10)]:
        setup = rng.choice(SETUPS)
        entry = JournalEntry(
            user_id=user_id, trading_account_id=account.id, trade_id=trade.id,
            entry_date=trade.close_time, setup=setup,
            emotion_before=rng.choice(EMOTIONS), emotion_during=rng.choice(EMOTIONS),
            emotion_after="calm" if trade.net_profit > 0 else rng.choice(["frustrated", "calm"]),
            confidence=rng.randint(2, 5),
            fear=rng.random() < 0.2, greed=rng.random() < 0.15,
            revenge=rng.random() < 0.1, fomo=rng.random() < 0.2, boredom=rng.random() < 0.1,
            discipline=rng.randint(2, 5), rule_adherence=rng.random() < 0.75,
            reason_entry=f"{setup} — {symbol}",
            reason_exit="TP sesuai rencana" if trade.net_profit > 0 else "SL — validasi ulang",
            notes=rng.choice(NOTES_ID),
            lesson="Tetap disiplin dengan rencana." if trade.net_profit > 0 else "Jangan pindah SL.",
            plan_match=rng.random() < 0.7,
        )
        db.add(entry)
        db.flush()
        for tag_name in rng.sample(TAG_NAMES, rng.randint(1, 2)):
            tag = db.query(Tag).filter(Tag.user_id == user_id, Tag.name == tag_name).first()
            if tag is None:
                tag = Tag(user_id=user_id, name=tag_name)
                db.add(tag)
                db.flush()
            db.execute(
                trade_tags.insert().values(journal_entry_id=entry.id, tag_id=tag.id)
            )

    for i in range(6):
        db.add(PsychologyEntry(
            user_id=user_id, trading_account_id=account.id, ts=_dt(trading_days[min(i * 9, len(trading_days) - 1)], 12, 0),
            mood=rng.choice(EMOTIONS), confidence=rng.randint(2, 5), focus=rng.randint(2, 5),
            notes="Sesi cukup fokus, mengikuti rencana harian.",
        ))

    return account


def _dt(day, hour: int, minute: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=_TZ)


def _group_by_month(trades: list[Trade]) -> list[tuple[object, list[Trade]]]:
    groups: dict[tuple[int, int], list[Trade]] = {}
    for t in trades:
        key = (t.close_time.year, t.close_time.month)
        groups.setdefault(key, []).append(t)
    out = []
    for (y, m), ts in groups.items():
        out.append((datetime(y, m, 1, tzinfo=_TZ).date(), ts))
    return out
