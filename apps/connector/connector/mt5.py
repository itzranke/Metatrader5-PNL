"""Adapter baca MT5 (read-only) — MetaTrader5 lib dipakai bila tersedia.

FakeMT5 menyediakan data sintetis untuk dev/test tanpa terminal MT5.
Antarmuka minimal agar engine tidak peduli sumber data.
"""
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

try:  # lib resmi MetaTrader5 hanya jalan di Windows + terminal MT5
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover
    mt5 = None


@dataclass
class MT5Account:
    login: int
    server: str
    name: str
    currency: str
    leverage: int
    balance: float
    equity: float


@dataclass
class MT5Deal:
    deal_ticket: int
    order_ticket: int
    time: datetime
    type: int  # 0 buy, 1 sell, 2 buy_close, 3 sell_close
    symbol: str
    volume: float
    price: float
    profit: float
    swap: float
    commission: float
    comment: str


@dataclass
class MT5Position:
    ticket: int
    symbol: str
    side: str  # buy | sell
    volume: float
    open_price: float
    open_time: datetime
    current_price: float
    floating_pnl: float
    sl: float | None
    tp: float | None


@dataclass
class MTTick:
    """Harga terkini simbol (BLUEPRINT §14 — live tick capture MAE/MFE).

    low/high = rentang harga sejak posisi terbuka; hanya diisi FakeMT5
    (walk sintetis). Adapter MT5 nyata mengisi bid/ask per polling, dan
    engine mengakumulasi MAE/MFE dari bid/ask tersebut.
    """

    bid: float
    ask: float
    low: float | None = None
    high: float | None = None


class MT5Adapter:
    """Wrapper read-only atas MetaTrader5 lib."""

    def __init__(self, login: str, server: str, password: str):
        self.login = login
        self.server = server
        self._password = password

    def connect(self) -> bool:
        if mt5 is None:
            return False
        return bool(mt5.initialize(login=int(self.login), server=self.server, password=self._password))

    def shutdown(self) -> None:
        if mt5 is not None:
            mt5.shutdown()

    def account_info(self) -> MT5Account | None:
        info = mt5.account_info()
        if info is None:
            return None
        return MT5Account(
            login=info.login, server=info.server or "", name=info.name or "",
            currency=info.currency or "USD", leverage=info.leverage or 0,
            balance=float(info.balance or 0), equity=float(info.equity or 0),
        )

    def history_deals(self, from_time: datetime) -> list[MT5Deal]:
        deals = mt5.history_deals_get(from_time) or []
        out = []
        for d in deals:
            if d.symbol is None or d.entry == 0:  # skip balance/credit entries
                continue
            out.append(
                MT5Deal(
                    deal_ticket=int(d.ticket), order_ticket=int(d.order or 0),
                    time=datetime.fromtimestamp(d.time, tz=UTC),
                    type=int(d.type), symbol=str(d.symbol), volume=float(d.volume),
                    price=float(d.price), profit=float(d.profit), swap=float(d.swap),
                    commission=float(d.commission), comment=str(d.comment or ""),
                )
            )
        return out

    def positions(self) -> list[MT5Position]:
        poss = mt5.positions_get() or []
        out = []
        for p in poss:
            if p.symbol is None:
                continue
            out.append(
                MT5Position(
                    ticket=int(p.ticket), symbol=str(p.symbol),
                    side="buy" if p.type == 0 else "sell", volume=float(p.volume),
                    open_price=float(p.price_open),
                    open_time=datetime.fromtimestamp(p.time, tz=UTC),
                    current_price=float(p.price_current),
                    floating_pnl=float(p.profit), sl=float(p.sl) if p.sl else None,
                    tp=float(p.tp) if p.tp else None,
                )
            )
        return out

    def current_tick(self, position: MT5Position) -> MTTick | None:
        """Tick terkini simbol posisi (untuk akumulasi MAE/MFE live)."""
        if mt5 is None:
            return None
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            return None
        return MTTick(bid=float(tick.bid), ask=float(tick.ask))


SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"]


class FakeMT5:
    """Data sintetis deterministik — meniru antarmuka MT5Adapter untuk dev/test."""

    def __init__(self, login: str = "12345678", server: str = "Srv-Demo", seed: int = 42,
                 fixed_walks: dict[int, dict] | None = None):
        self.login = login
        self.server = server
        self._rng = random.Random(seed)
        self._deals: list[MT5Deal] = []
        self._positions: list[MT5Position] = []
        self._next_ticket = 1000
        self._walks: dict[int, dict] = {}
        self._fixed_walks = fixed_walks or {}

    def _walk_for(self, pos: MT5Position) -> dict:
        if pos.ticket in self._fixed_walks:
            return self._fixed_walks[pos.ticket]
        if pos.ticket in self._walks:
            return self._walks[pos.ticket]
        # random walk deterministik (seed = ticket): 30 langkah dari open_price
        rng = random.Random(pos.ticket)
        price = pos.open_price
        low = high = price
        step = max(pos.open_price * 0.0006, 1e-6)  # skala wajar per langkah
        for _ in range(30):
            price += rng.uniform(-1.0, 1.0) * step
            low = min(low, price)
            high = max(high, price)
        self._walks[pos.ticket] = {"low": low, "high": high, "price": price}
        return self._walks[pos.ticket]

    def current_tick(self, position: MT5Position) -> MTTick | None:
        w = self._walk_for(position)
        return MTTick(bid=w["price"], ask=w["price"], low=w["low"], high=w["high"])

    def connect(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    def account_info(self) -> MT5Account:
        return MT5Account(
            login=int(self.login), server=self.server, name="Fake Trader",
            currency="USD", leverage=100, balance=10000.0, equity=10050.0,
        )

    def seed_deals(self, count: int, days_back: int = 60) -> None:
        now = datetime.now(UTC)
        for i in range(count):
            # deal tertua maksimal (days_back - 1) hari — hindari jatuh tepat di
            # batas from_time engine (now - 60 hari) yang membuatnya tersaring
            t = now - timedelta(
                days=(days_back - 1) * (1 - i / max(count, 1)), hours=self._rng.randint(1, 12)
            )
            sym = self._rng.choice(SYMBOLS)
            price = round(1.08 + self._rng.uniform(-0.02, 0.02), 5)
            is_close = i % 2 == 1
            self._deals.append(
                MT5Deal(
                    deal_ticket=self._next_ticket, order_ticket=self._next_ticket - 1,
                    time=t, type=(2 if is_close else 0), symbol=sym,
                    volume=round(self._rng.choice([0.1, 0.2, 0.5]), 2),
                    price=price, profit=round(self._rng.uniform(-50, 80), 2) if is_close else 0.0,
                    swap=0.0, commission=-1.5, comment="",
                )
            )
            self._next_ticket += 1

    def seed_positions(self, count: int = 2) -> None:
        now = datetime.now(UTC)
        for _ in range(count):
            sym = self._rng.choice(SYMBOLS)
            price = round(1.08 + self._rng.uniform(-0.02, 0.02), 5)
            self._positions.append(
                MT5Position(
                    ticket=self._next_ticket, symbol=sym,
                    side=self._rng.choice(["buy", "sell"]), volume=0.2,
                    open_price=price, open_time=now - timedelta(hours=3),
                    current_price=price + 0.0008, floating_pnl=8.5,
                    sl=None, tp=None,
                )
            )
            self._next_ticket += 1

    def history_deals(self, from_time: datetime) -> list[MT5Deal]:
        return [d for d in self._deals if d.time >= from_time]

    def positions(self) -> list[MT5Position]:
        return list(self._positions)
