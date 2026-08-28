"""Smoke test model inti: user, akun, koneksi, device — relasi & unique."""
import pytest
from sqlalchemy.exc import IntegrityError

from packages.db import SessionLocal
from packages.db.models import (
    Broker,
    ConnectorDevice,
    MT5Connection,
    TradingAccount,
    User,
)


def test_user_account_connection_flow():
    with SessionLocal() as db:
        broker = Broker(name="HF Markets", server="HFMarketsGlobal-Demo", is_demo=True)
        db.add(broker)
        db.flush()

        user = User(username="andi", email="andi@example.com", password_hash="x")
        db.add(user)
        db.flush()
        assert user.id is not None
        assert user.session_version == 0
        assert user.role == "user"

        acc = TradingAccount(
            user_id=user.id,
            broker_id=broker.id,
            name="Demo HF",
            login="49155931",
            server="HFMarketsGlobal-Demo",
            kind="mt5",
        )
        db.add(acc)
        db.flush()

        device = ConnectorDevice(
            user_id=user.id,
            device_name="PC Kantor",
            device_key_hash="hash",
            client_id="cli-123",
        )
        db.add(device)
        db.flush()

        conn = MT5Connection(
            user_id=user.id,
            trading_account_id=acc.id,
            connector_device_id=device.id,
        )
        db.add(conn)
        db.commit()

        # relasi
        assert user.accounts[0].id == acc.id
        assert user.devices[0].id == device.id
        assert acc.connection.id == conn.id


def test_duplicate_account_login_server_ditolak():
    with SessionLocal() as db:
        u1 = User(username="budi", email="budi@example.com", password_hash="x")
        db.add(u1)
        db.flush()
        db.add(
            TradingAccount(
                user_id=u1.id, name="A", login="12345", server="Srv-Demo", kind="demo"
            )
        )
        db.commit()

    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(
            TradingAccount(
                user_id=u1.id, name="B", login="12345", server="Srv-Demo", kind="demo"
            )
        )
        db.commit()
    db.rollback()


def test_username_email_unique():
    with SessionLocal() as db:
        db.add(User(username="citra", email="citra@example.com", password_hash="x"))
        db.commit()
    with SessionLocal() as db, pytest.raises(IntegrityError):
        db.add(User(username="citra", email="citra2@example.com", password_hash="x"))
        db.commit()
    db.rollback()
