"""Outbox offline — antrian JSONL payload gagal kirim (idempoten di server)."""
import json
import os


class Outbox:
    """Antrian append-only di disk; payload dikirim ulang saat online."""

    def __init__(self, config_path: str):
        cfg_dir = os.path.dirname(config_path) if config_path else "."
        self.path = os.path.join(cfg_dir, "outbox.jsonl")

    def push(self, item: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item) + "\n")

    def all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        items = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # baris korup (crash lama) diabaikan — tidak memblokir
        return items

    def remove(self, item: dict) -> None:
        """Hapus satu item (rewrite file — outbox kecil, aman)."""
        items = self.all()
        remaining = [it for it in items if it is not item and json.dumps(it) != json.dumps(item)]
        with open(self.path, "w", encoding="utf-8") as f:
            for it in remaining:
                f.write(json.dumps(it) + "\n")
        if not remaining:
            os.remove(self.path) if os.path.exists(self.path) else None
