"""Konfigurasi connector (connector.json) — load/save, tanpa library eksternal."""
import json
import os

DEFAULT_PATH = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), "mt5-journal", "connector.json"
)

DEFAULTS = {
    "server_url": os.environ.get("CONNECTOR_SERVER_URL", "https://api.mt5journal.app"),
    "device_id": None,
    "device_key": None,
    "mt5_login": None,
    "mt5_server": None,
    "mt5_password_encrypted": None,
}


def load_config(path: str | None = None) -> dict:
    cfg_path = path or DEFAULT_PATH
    cfg = dict(DEFAULTS)
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    cfg["_path"] = cfg_path
    return cfg


def save_config(cfg: dict, path: str | None = None) -> None:
    cfg_path = path or cfg.get("_path") or DEFAULT_PATH
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    payload = {k: v for k, v in cfg.items() if not k.startswith("_")}
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_mt5_password(path: str | None = None) -> str | None:
    """Baca password MT5 dari file terpisah (mode dev; production: DPAPI)."""
    cfg_path = path or DEFAULT_PATH
    pw_path = cfg_path.replace("connector.json", "mt5_password.txt")
    if os.path.exists(pw_path):
        with open(pw_path, encoding="utf-8") as f:
            return f.read().strip()
    return None
