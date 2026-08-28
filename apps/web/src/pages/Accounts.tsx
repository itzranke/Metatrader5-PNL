import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";

interface Account {
  id: number;
  name: string;
  login: string;
  server: string;
  kind: string;
  currency: string;
  leverage: number | null;
  broker_tz: number;
  is_active: boolean;
  created_at: string;
  connection_state: string | null;
  last_synced_at: string | null;
}

interface BrokerPreset {
  name: string;
  login: string;
  server: string;
}

export function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [presets, setPresets] = useState<BrokerPreset[]>([]);
  const [presetLogin, setPresetLogin] = useState("");
  const [presetServer, setPresetServer] = useState("");
  const [accountName, setAccountName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setAccounts(await api<Account[]>("/accounts"));
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat akun"));
    api<BrokerPreset[]>("/meta/broker-presets")
      .then((p) => {
        setPresets(p);
        const hf = p.find((x) => x.login);
        if (hf) {
          setPresetLogin(hf.login);
          setPresetServer(hf.server);
        }
      })
      .catch(() => undefined);
  }, [load]);

  async function createDemo() {
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await api("/accounts", { method: "POST", body: JSON.stringify({ kind: "demo", name: accountName || "Data Contoh" }) });
      setInfo("Akun Data Contoh dibuat — 60–90 hari data trading siap dieksplor.");
      setAccountName("");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal membuat akun demo");
    } finally {
      setBusy(false);
    }
  }

  async function createHf(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      await api("/accounts", {
        method: "POST",
        body: JSON.stringify({ kind: "mt5", name: accountName || "HF Markets Demo", login: presetLogin, server: presetServer }),
      });
      setInfo("Akun HF Markets ditambahkan. Hubungkan connector untuk sync (Phase 4).");
      setAccountName("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menambah akun");
    } finally {
      setBusy(false);
    }
  }

  async function removeAccount(id: number) {
    setError(null);
    try {
      await api(`/accounts/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal menghapus akun");
    }
  }

  return (
    <div>
      <h1 className="title">Akun</h1>
      <p className="muted">Kelola akun MT5 kamu. Belum punya MT5? Coba Data Contoh dulu.</p>

      {error && <p className="error" role="alert">{error}</p>}
      {info && <p className="info" role="status">{info}</p>}

      <div className="account-actions">
        <div className="card">
          <h2 className="title">Data Contoh</h2>
          <p className="muted">Akun sintetis dengan 60–90 hari riwayat trading — tanpa MT5.</p>
          <div className="row">
            <button className="btn btn-primary" onClick={createDemo} disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}
              Buat Data Contoh
            </button>
          </div>
        </div>

        <div className="card">
          <h2 className="title">Hubungkan Akun MT5</h2>
          <form className="form" onSubmit={createHf}>
            <div className="field">
              <label htmlFor="acc-name">Nama Akun</label>
              <input id="acc-name" value={accountName} onChange={(e) => setAccountName(e.target.value)} placeholder="mis. Akun Demo HF" />
            </div>
            <div className="field">
              <label htmlFor="acc-login">Login</label>
              <input id="acc-login" value={presetLogin} onChange={(e) => setPresetLogin(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="acc-server">Server</label>
              <input id="acc-server" value={presetServer} onChange={(e) => setPresetServer(e.target.value)} required />
            </div>
            <button className="btn btn-secondary" type="button" onClick={() => {
              const hf = presets.find((x) => x.login);
              if (hf) {
                setPresetLogin(hf.login);
                setPresetServer(hf.server);
                setAccountName("HF Markets Demo");
              }
            }}>
              Isi Akun Demo HF Markets
            </button>
            <p className="muted note">Password MT5 tidak pernah disimpan di sini — diisi di connector saat pairing.</p>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy && <span className="spinner" aria-hidden="true" />}
              Tambah Akun
            </button>
          </form>
        </div>
      </div>

      <h2 className="title">Daftar Akun</h2>
      {accounts.length === 0 ? (
        <div className="card empty">
          <span className="title">Belum ada akun</span>
          <span className="muted">Buat Data Contoh atau hubungkan akun MT5 kamu.</span>
        </div>
      ) : (
        <div className="account-grid">
          {accounts.map((a) => (
            <div className="card" key={a.id}>
              <div className="row spread">
                <b>{a.name}</b>
                <span className={`chip ${a.kind === "demo" ? "chip-demo" : ""}`}>
                  {a.kind === "demo" ? "DATA CONTOH" : "MT5"}
                </span>
              </div>
              <p className="muted">
                {a.login} @ {a.server} · {a.currency}
                {a.connection_state ? ` · ${a.connection_state}` : " · belum terhubung"}
              </p>
              <button className="btn btn-ghost" onClick={() => removeAccount(a.id)}>
                Hapus
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
