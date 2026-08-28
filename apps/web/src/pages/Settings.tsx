import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../auth/AuthContext";

interface Me {
  id: number;
  username: string;
  email: string;
  email_verified: boolean;
  role: string;
  locale: string;
  base_currency: string;
  created_at: string;
}
interface SessionRow {
  id: number;
  device_name: string;
  ip: string;
  created_at: string;
  last_seen_at: string | null;
  is_current: boolean;
}
interface Account { id: number; name: string; kind: string; }

export function SettingsPage() {
  const { user, updateUser } = useAuth();
  const [me, setMe] = useState<Me | null>(user as Me | null);
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [username, setUsername] = useState("");
  const [baseCurrency, setBaseCurrency] = useState("USD");
  const [locale, setLocale] = useState("id");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadSessions = useCallback(async () => {
    setSessions(await api<SessionRow[]>("/auth/sessions"));
  }, []);

  useEffect(() => {
    api<Me>("/auth/me").then((m) => {
      setMe(m);
      setUsername(m.username);
      setBaseCurrency(m.base_currency);
      setLocale(m.locale);
    }).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat profil"));
    loadSessions().catch(() => undefined);
    api<Account[]>("/accounts").then(setAccounts).catch(() => undefined);
  }, [loadSessions]);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setInfo(null);
    try {
      const updated = await api<Me>("/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ username, base_currency: baseCurrency, locale }),
      });
      setMe(updated);
      updateUser(updated);
      setInfo("Profil diperbarui.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan profil");
    } finally { setBusy(false); }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setInfo(null);
    try {
      await api("/auth/me/password", {
        method: "POST",
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      setOldPassword(""); setNewPassword("");
      setInfo("Password diganti — sesi lain dicabut.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mengganti password");
    } finally { setBusy(false); }
  }

  async function revokeSession(id: number) {
    setError(null);
    try {
      await api(`/auth/sessions/${id}`, { method: "DELETE" });
      await loadSessions();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mencabut sesi");
    }
  }

  const activeAccount = accounts.find((a) => a.kind === "mt5") ?? accounts[0];

  return (
    <div>
      <h1 className="title">Pengaturan</h1>
      {error && <p className="error" role="alert">{error}</p>}
      {info && <p className="info" role="status">{info}</p>}

      <form className="card form" onSubmit={saveProfile}>
        <h2 className="title">Profil</h2>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="s-username">Username</label>
            <input id="s-username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} required />
          </div>
          <div className="field">
            <label htmlFor="s-email">Email</label>
            <input id="s-email" value={me?.email ?? ""} disabled />
          </div>
          <div className="field">
            <label htmlFor="s-currency">Mata uang</label>
            <select id="s-currency" value={baseCurrency} onChange={(e) => setBaseCurrency(e.target.value)}>
              {["USD", "EUR", "IDR", "SGD", "JPY"].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="s-locale">Bahasa</label>
            <select id="s-locale" value={locale} onChange={(e) => setLocale(e.target.value)}>
              <option value="id">Indonesia</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy && <span className="spinner" aria-hidden="true" />}
          Simpan Profil
        </button>
      </form>

      <form className="card form" onSubmit={changePassword}>
        <h2 className="title">Ganti Password</h2>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="s-old">Password lama</label>
            <input id="s-old" type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="s-new">Password baru (min. 8 karakter)</label>
            <input id="s-new" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} minLength={8} required />
          </div>
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy && <span className="spinner" aria-hidden="true" />}
          Ganti Password
        </button>
      </form>

      <div className="card">
        <h2 className="title">Sesi Aktif</h2>
        {sessions.length === 0 ? (
          <p className="muted">Tidak ada sesi.</p>
        ) : (
          <table className="table">
            <thead><tr><th>Perangkat</th><th>IP</th><th>Terakhir aktif</th><th></th></tr></thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td>{s.device_name || "Perangkat web"} {s.is_current && <span className="chip chip-demo">SESI INI</span>}</td>
                  <td>{s.ip || "—"}</td>
                  <td>{s.last_seen_at ? new Date(s.last_seen_at).toLocaleString("id-ID") : "—"}</td>
                  <td>
                    {!s.is_current && (
                      <button className="btn btn-ghost" onClick={() => revokeSession(s.id)}>Cabut</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <h2 className="title">Export Data (CSV)</h2>
        <p className="muted">
          {activeAccount
            ? `Unduh data akun "${activeAccount.name}":`
            : "Buat akun dulu untuk mengekspor data."}
        </p>
        {activeAccount && (
          <div className="row">
            <a className="btn btn-secondary" href={`/api/v1/accounts/${activeAccount.id}/export/trades.csv`} download>
              Trade (CSV)
            </a>
            <a className="btn btn-secondary" href={`/api/v1/accounts/${activeAccount.id}/export/journal.csv`} download>
              Jurnal (CSV)
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
