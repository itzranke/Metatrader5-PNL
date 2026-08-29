"""Test Phase 9 — live tick capture MAE/MFE di connector (BLUEPRINT §14).

Gate: excursion dihitung dari tick path (low/high), kumulatif antar sync,
arah side benar, dan payload sync menyertakan excursions.
"""
from datetime import UTC, datetime, timedelta

from connector.client import SyncEngine
from connector.mt5 import FakeMT5, MT5Position


def _pos(ticket: int, side: str = "buy", open_price: float = 1.0800) -> MT5Position:
    return MT5Position(
        ticket=ticket, symbol="EURUSD", side=side, volume=0.1,
        open_price=open_price, open_time=datetime.now(UTC) - timedelta(hours=2),
        current_price=open_price, floating_pnl=0.0, sl=None, tp=None,
    )


class _RecordingClient:
    """ApiClient tiruan — merekam payload sync, tidak memanggil server."""

    def __init__(self):
        self.payloads: list[dict] = []

    def sync(self, device_id, device_key, payload):
        self.payloads.append(payload)
        return {"accepted": 0, "duplicates": 0, "last_ticket": payload.get("last_ticket"), "state": "SYNCED"}


def _engine(fake: FakeMT5) -> tuple[SyncEngine, _RecordingClient]:
    client = _RecordingClient()
    engine = SyncEngine(client=client, mt5=fake, cfg={}, outbox=None)
    return engine, client


def test_excursion_buy_from_fixed_walk():
    # buy 1.0800; walk low 1.0780 (MAE 0.002), high 1.0900 (MFE 0.010)
    fake = FakeMT5(fixed_walks={101: {"low": 1.0780, "high": 1.0900, "price": 1.0850}})
    fake._positions = [_pos(101)]
    engine, _ = _engine(fake)
    out = engine._update_excursions(fake.positions())
    assert out == [{"ticket": "101", "mae_pts": 0.002, "mfe_pts": 0.010, "samples": 1}]


def test_excursion_sell_side():
    # sell 1.0800: adverse = high - open = 0.010, fav = open - low = 0.002
    fake = FakeMT5(fixed_walks={202: {"low": 1.0780, "high": 1.0900, "price": 1.0860}})
    fake._positions = [_pos(202, side="sell")]
    engine, _ = _engine(fake)
    out = engine._update_excursions(fake.positions())
    assert out[0]["mae_pts"] == 0.010 and out[0]["mfe_pts"] == 0.002


def test_excursion_cumulative_across_syncs():
    # sync 1: low 1.0790 → mae 0.001; sync 2: low lebih dalam 1.0775 → mae 0.0025
    fake = FakeMT5(fixed_walks={303: {"low": 1.0790, "high": 1.0860, "price": 1.0830}})
    fake._positions = [_pos(303)]
    engine, _ = _engine(fake)
    engine._update_excursions(fake.positions())
    assert engine.cfg["excursions"]["303"]["mae"] == 0.001

    fake._fixed_walks[303] = {"low": 1.0775, "high": 1.0875, "price": 1.0840}
    out = engine._update_excursions(fake.positions())
    assert out[0]["mae_pts"] == 0.0025 and out[0]["mfe_pts"] == 0.0075
    assert out[0]["samples"] == 2  # akumulasi polling


def test_sync_once_payload_includes_excursions():
    fake = FakeMT5(fixed_walks={404: {"low": 1.0790, "high": 1.0880, "price": 1.0840}})
    fake._positions = [_pos(404)]
    fake._deals = []
    engine, client = _engine(fake)
    engine.sync_once(device_id=1, device_key="k")
    assert client.payloads, "sync harus dipanggil"
    p = client.payloads[0]
    assert p["excursions"] == [{"ticket": "404", "mae_pts": 0.001, "mfe_pts": 0.008, "samples": 1}]
    assert p["positions"][0]["ticket"] == "404"


def test_excursion_mae_mfe_non_negative():
    # harga tidak pernah melawan posisi → MAE 0, MFE 0
    fake = FakeMT5(fixed_walks={505: {"low": 1.0800, "high": 1.0800, "price": 1.0800}})
    fake._positions = [_pos(505)]
    engine, _ = _engine(fake)
    out = engine._update_excursions(fake.positions())
    assert out[0]["mae_pts"] == 0.0 and out[0]["mfe_pts"] == 0.0
