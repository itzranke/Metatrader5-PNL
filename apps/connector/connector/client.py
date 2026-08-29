"""HTTP client connector — stdlib urllib, backoff exponensial, outbox-aware."""
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

from . import crypto
from .outbox import Outbox


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class ApiClient:
    """Klien minimal ke API server (pairing, heartbeat, sync)."""

    def __init__(self, server_url: str, timeout: float = 15.0):
        self.base = server_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None,
                 headers: dict | None = None) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, method=method,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "mt5-journal-connector/0.1",
                **(headers or {}),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("detail", str(e))
            except Exception:
                detail = str(e)
            raise ApiError(e.code, detail) from None

    # ---- pairing ----
    def pair(self, code: str, client_id: str, device_name: str = "", version: str = "") -> dict:
        return self._request("POST", "/api/v1/connector/pair", {
            "code": code, "client_id": client_id,
            "device_name": device_name, "version": version,
        })

    # ---- device auth ----
    def heartbeat(self, device_id: int, device_key: str) -> dict:
        return self._request("POST", "/api/v1/connector/heartbeat",
                             headers=crypto.auth_headers(device_id, device_key))

    def sync(self, device_id: int, device_key: str, payload: dict) -> dict:
        headers = crypto.auth_headers(device_id, device_key)
        return self._request("POST", "/api/v1/connector/sync", payload, headers=headers)

    # ---- retry dengan backoff (tanpa threading — dipanggil loop engine) ----
    def call_with_retry(self, fn, attempts: int = 5, base_delay: float = 2.0):
        delay = base_delay
        for i in range(attempts):
            try:
                return fn()
            except (ApiError, urllib.error.URLError):
                if i == attempts - 1:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
        raise ApiError(0, "unreachable")


class SyncEngine:
    """Loop sinkronisasi: heartbeat + sync batch + drain outbox.

    State machine BLUEPRINT §8.7: DISCONNECTED → PAIRING → CONNECTED →
    SYNCING → SYNCED; error → RECONNECTING dengan backoff.
    """

    def __init__(self, client: ApiClient, mt5, cfg: dict, outbox: Outbox | None = None,
                 batch_size: int = 500):
        self.client = client
        self.mt5 = mt5
        self.cfg = cfg
        self.outbox = outbox or Outbox(cfg.get("_path", ""))
        self.batch_size = batch_size
        self.state = "DISCONNECTED"

    # ---- outbox ----
    def _enqueue(self, payload: dict) -> None:
        self.outbox.push({"ts": datetime.now(UTC).isoformat(), "payload": payload})

    def drain_outbox(self, device_id: int, device_key: str) -> tuple[int, int]:
        """Kirim ulang payload yang gagal saat offline → idempoten di server."""
        sent = 0
        items = self.outbox.all()
        for item in items:
            try:
                self.client.sync(device_id, device_key, item["payload"])
            except (ApiError, urllib.error.URLError):
                break  # masih offline — berhenti, coba lagi siklus berikutnya
            self.outbox.remove(item)
            sent += 1
        return sent, len(items) - sent

    # ---- sync sekali (unit kerja utama) ----
    def _update_excursions(self, mt5_positions: list) -> list[dict]:
        """Akumulasi MAE/MFE live per posisi (BLUEPRINT §14 level 1).

        State kumulatif disimpan di cfg['excursions'] (bertahan antar sync
        dalam satu proses; adikodifikasikan per ticket). MTTick dari FakeMT5
        membawa low/high walk → excursion penuh; adapter nyata hanya bid/ask
        → excursion bertahap (mendekati maksimum seiring polling).
        """
        ex = self.cfg.setdefault("excursions", {})
        out: list[dict] = []
        for p in mt5_positions:
            tick = self.mt5.current_tick(p)
            if tick is None:
                continue
            st = ex.setdefault(str(p.ticket), {"mae": 0.0, "mfe": 0.0, "samples": 0})
            if p.side == "buy":
                adverse = max(0.0, p.open_price - (tick.low if tick.low is not None else tick.bid))
                fav = max(0.0, (tick.high if tick.high is not None else tick.ask) - p.open_price)
            else:
                adverse = max(0.0, (tick.high if tick.high is not None else tick.ask) - p.open_price)
                fav = max(0.0, p.open_price - (tick.low if tick.low is not None else tick.bid))
            st["mae"] = max(st["mae"], round(adverse, 8))
            st["mfe"] = max(st["mfe"], round(fav, 8))
            st["samples"] += 1
            out.append({
                "ticket": str(p.ticket), "mae_pts": st["mae"], "mfe_pts": st["mfe"],
                "samples": st["samples"],
            })
        return out

    def sync_once(self, device_id: int, device_key: str) -> dict:
        self.state = "SYNCING"
        # 1. posisi (selalu penuh) + MAE/MFE live dari tick
        mt5_positions = self.mt5.positions()
        positions = [
            {
                "ticket": str(p.ticket), "symbol": p.symbol, "side": p.side,
                "volume": p.volume, "open_price": p.open_price,
                "open_time": p.open_time.isoformat(), "current_price": p.current_price,
                "floating_pnl": p.floating_pnl, "sl": p.sl, "tp": p.tp,
            }
            for p in mt5_positions
        ]
        excursions = self._update_excursions(mt5_positions)
        # 2. deals inkremental (60 hari pertama, lalu sejak ticket terakhir)
        last_ticket = self.cfg.get("last_deal_ticket")
        from_time = datetime.now(UTC) - timedelta(days=60)
        deals = self.mt5.history_deals(from_time)
        if last_ticket:
            deals = [d for d in deals if d.deal_ticket > int(last_ticket)]
        deals.sort(key=lambda d: d.deal_ticket)

        account = self.mt5.account_info()
        login = str(account.login if account else self.mt5.login)
        server = self.mt5.server

        result = {"accepted": 0, "duplicates": 0, "last_ticket": None}
        # tanpa deal baru pun tetap kirim (posisi + MAE/MFE live)
        batches = [deals[i : i + self.batch_size] for i in range(0, len(deals), self.batch_size)]
        if not batches and positions:
            batches = [[]]
        for i, batch in enumerate(batches):
            payload = {
                "login": login, "server": server, "kind": "incremental" if last_ticket else "full",
                "last_ticket": str(batch[-1].deal_ticket) if batch else last_ticket,
                "deals": [
                    {
                        "deal_ticket": str(d.deal_ticket), "order_ticket": str(d.order_ticket),
                        "time": d.time.isoformat(), "type": d.type, "symbol": d.symbol,
                        "volume": d.volume, "price": d.price, "profit": d.profit,
                        "swap": d.swap, "commission": d.commission, "comment": d.comment,
                    }
                    for d in batch
                ],
                "positions": positions if i == 0 else [],  # posisi cukup di batch pertama
                "excursions": excursions if i == 0 else [],
            }
            try:
                resp = self.client.sync(device_id, device_key, payload)
                result["accepted"] += resp.get("accepted", 0)
                result["duplicates"] += resp.get("duplicates", 0)
                result["last_ticket"] = resp.get("last_ticket")
            except (ApiError, urllib.error.URLError):
                self._enqueue(payload)  # offline → outbox, lanjut nanti
                result["offline"] = True
                break
            if result.get("last_ticket"):
                self.cfg["last_deal_ticket"] = result["last_ticket"]

        self.state = "SYNCED"
        return result

    # ---- loop utama ----
    def run(self, device_id: int, device_key: str, once: bool = False) -> None:
        self.state = "CONNECTED"
        while True:
            try:
                self.client.heartbeat(device_id, device_key)
                self.drain_outbox(device_id, device_key)
                self.sync_once(device_id, device_key)
            except (ApiError, urllib.error.URLError):
                self.state = "RECONNECTING"
                if once:
                    break
                time.sleep(30)  # backoff sederhana; siklus berikutnya coba lagi
            if once:
                break
            time.sleep(30)
