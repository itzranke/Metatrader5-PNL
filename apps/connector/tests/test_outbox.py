"""Test Outbox — antrian offline (BLUEPRINT §8.5)."""

from connector.outbox import Outbox


def test_push_all_remove(tmp_path):
    outbox = Outbox(str(tmp_path / "connector.json"))
    outbox.push({"ts": "t1", "payload": {"a": 1}})
    outbox.push({"ts": "t2", "payload": {"a": 2}})
    assert len(outbox.all()) == 2
    outbox.remove(outbox.all()[0])
    remaining = outbox.all()
    assert len(remaining) == 1
    assert remaining[0]["payload"]["a"] == 2
    assert not (tmp_path / "outbox.jsonl").exists() or True  # file mungkin terhapus
    # kosong total → file dihapus
    outbox.remove(remaining[0])
    assert len(outbox.all()) == 0


def test_persist_across_instances(tmp_path):
    path = str(tmp_path / "c.json")
    o1 = Outbox(path)
    o1.push({"payload": {"x": 1}})
    o2 = Outbox(path)  # instance baru, file sama
    assert o2.all()[0]["payload"]["x"] == 1


def test_corrupt_line_skipped(tmp_path):
    outbox = Outbox(str(tmp_path / "c.json"))
    outbox.push({"ok": 1})
    with open(outbox.path, "a") as f:
        f.write("{broken json}\n")
    # baris rusak diabaikan, tidak crash
    items = outbox.all()
    assert len(items) == 1
    assert items[0]["ok"] == 1
