"""CLI connector — `python -m connector [command]`.

Commands: pair <CODE> · sync [--once] · status · reset
"""
import argparse
import json
import sys

from .client import ApiClient, SyncEngine
from .config import load_config, save_config
from .crypto import new_client_id
from .mt5 import FakeMT5, MT5Adapter


def cmd_pair(cfg: dict, args) -> int:
    client = ApiClient(cfg["server_url"])
    device_name = args.device_name or "PC"
    result = client.pair(args.code, new_client_id(), device_name=device_name, version="0.1.0")
    cfg["device_id"] = result["device_id"]
    cfg["device_key"] = result["device_key"]
    save_config(cfg)
    print(f"Berhasil dipair: device_id={result['device_id']}")
    print("Simpan device_key ini baik-baik (tidak bisa dilihat lagi).")
    return 0


def cmd_sync(cfg: dict, args) -> int:
    if not cfg.get("device_id") or not cfg.get("device_key"):
        print("Belum dipair. Jalankan: connector pair <KODE>")
        return 1
    client = ApiClient(cfg["server_url"])
    # mode dev/test: FakeMT5 bila tidak ada MT5 lib atau --fake
    import connector.mt5 as mt5_mod

    if args.fake or mt5_mod.mt5 is None:
        mt5 = FakeMT5(seed=args.seed)
        mt5.seed_deals(40, days_back=30)
        mt5.seed_positions(2)
    else:
        password = ""  # production: DPAPI decrypt
        mt5 = MT5Adapter(str(cfg.get("mt5_login", "")), cfg.get("mt5_server", ""), password)
        if not mt5.connect():
            print("Tidak bisa terhubung ke MT5 terminal.")
            return 1
    engine = SyncEngine(client, mt5, cfg)
    result = engine.sync_once(cfg["device_id"], cfg["device_key"])
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(cfg: dict) -> int:
    print(f"server_url : {cfg['server_url']}")
    print(f"device_id  : {cfg.get('device_id')}")
    print(f"mt5        : {cfg.get('mt5_login')}@{cfg.get('mt5_server')}")
    outbox = []
    import os

    p = os.path.join(os.path.dirname(cfg.get("_path", "")), "outbox.jsonl")
    if os.path.exists(p):
        with open(p) as f:
            outbox = [line for line in f if line.strip()]
    print(f"outbox     : {len(outbox)} item tertunda")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="connector", description="MT5 Journal Desktop Connector")
    parser.add_argument("--config", help="path connector.json")
    sub = parser.add_subparsers(dest="command", required=True)
    p_pair = sub.add_parser("pair", help="pairing dengan kode dari web")
    p_pair.add_argument("code")
    p_pair.add_argument("--device-name", default="")
    p_sync = sub.add_parser("sync", help="sinkronisasi sekali")
    p_sync.add_argument("--fake", action="store_true", help="pakai data sintetis (dev)")
    p_sync.add_argument("--seed", type=int, default=42)
    sub.add_parser("status", help="status connector")
    sub.add_parser("reset", help="hapus device_key (unpair)")

    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "pair":
        return cmd_pair(cfg, args)
    if args.command == "sync":
        return cmd_sync(cfg, args)
    if args.command == "status":
        return cmd_status(cfg)
    if args.command == "reset":
        cfg["device_id"] = None
        cfg["device_key"] = None
        save_config(cfg)
        print("Device unpair. Jalankan pair lagi bila perlu.")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
