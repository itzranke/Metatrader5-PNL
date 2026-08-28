import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";

interface Device {
  id: number;
  device_name: string;
  state: string;
  version: string;
  last_seen_at: string | null;
  created_at: string;
  accounts: string[];
}

const STATE_LABEL: Record<string, string> = {
  PAIRING: "Menunggu pairing",
  CONNECTED: "Terhubung",
  SYNCING: "Menyinkronkan",
  SYNCED: "Sinkron",
  RECONNECTING: "Menyambung ulang",
  DISCONNECTED: "Terputus",
  ERROR: "Galat",
};

export function ConnectorPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [code, setCode] = useState<string | null>(null);
  const [codeExpiry, setCodeExpiry] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setDevices(await api<Device[]>("/connector/devices"));
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat perangkat"));
  }, [load]);

  async function createCode() {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const r = await api<{ code: string; expires_at: string }>("/connector/pair-request", {
        method: "POST",
      });
      setCode(r.code);
      setCodeExpiry(r.expires_at);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal membuat kode pairing");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="title">Hubungkan Connector</h1>
      <p className="muted">
        Pasangkan aplikasi desktop (MT5 Journal Connector) ke akunmu agar trade tersinkron otomatis.
      </p>

      {error && <p className="error" role="alert">{error}</p>}
      {info && <p className="info" role="status">{info}</p>}

      <div className="card">
        <h2 className="title">1. Buat kode pairing</h2>
        <p className="muted">Kode berlaku 5 menit dan hanya bisa dipakai sekali.</p>
        <button className="btn btn-primary" onClick={createCode} disabled={busy}>
          {busy && <span className="spinner" aria-hidden="true" />}
          Buat Kode Pairing
        </button>

        {code && (
          <div className="pairing-box">
            <div className="pairing-code">{code}</div>
            <p className="muted note">
              Masukkan kode ini di aplikasi Connector (perintah: <code>connector pair {code}</code>).
              Berakhir {codeExpiry ? new Date(codeExpiry).toLocaleTimeString("id-ID") : ""}.
            </p>
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="title">2. Unduh & pasang Connector</h2>
        <ol className="muted steps">
          <li>Jalankan <b>connector.exe</b> di komputer dengan MT5 terpasang.</li>
          <li>Pilih <b>Pair</b>, masukkan kode pairing dari langkah 1.</li>
          <li>Pilih akun MT5 yang sudah didaftarkan, lalu biarkan tersinkron.</li>
        </ol>
        <p className="muted note">
          Password MT5 hanya disimpan di komputermu (DPAPI), tidak pernah dikirim ke server.
        </p>
      </div>

      <h2 className="title">Perangkat Terhubung</h2>
      {devices.length === 0 ? (
        <div className="card empty">
          <span className="title">Belum ada perangkat</span>
          <span className="muted">Buat kode pairing lalu pasangkan connector.</span>
        </div>
      ) : (
        <div className="account-grid">
          {devices.map((d) => (
            <div className="card" key={d.id}>
              <div className="row spread">
                <b>{d.device_name || `Device #${d.id}`}</b>
                <span className={`chip chip-${d.state === "SYNCED" || d.state === "CONNECTED" ? "demo" : "warn"}`}>
                  {STATE_LABEL[d.state] ?? d.state}
                </span>
              </div>
              <p className="muted">
                v{d.version || "?"} · terakhir{" "}
                {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString("id-ID") : "belum pernah"}
              </p>
              {d.accounts.length > 0 && (
                <ul className="muted note">
                  {d.accounts.map((a) => <li key={a}>{a}</li>)}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
