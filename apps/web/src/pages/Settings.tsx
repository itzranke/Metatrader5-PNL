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
interface MoneyRow { id: number; kind: "deposit" | "withdrawal"; amount: number; ts: string; method: string; note: string; }
interface MoneyList { net_deposits: number; total_deposits: number; total_withdrawals: number; items: MoneyRow[]; }

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
  const [money, setMoney] = useState<MoneyList | null>(null);
  const [moneyAccountId, setMoneyAccountId] = useState<number | null>(null);
  const [moneyAmount, setMoneyAmount] = useState("");
  const [moneyKind, setMoneyKind] = useState<"deposit" | "withdrawal">("deposit");
  const [moneyNote, setMoneyNote] = useState("");
  const [reportMonth, setReportMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadMoney = useCallback(async (accountId: number) => {
    setMoney(await api<MoneyList>(`/accounts/${accountId}/money`));
  }, []);

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
    api<Account[]>("/accounts").then((a) => {
      setAccounts(a);
      if (a.length > 0) {
        setMoneyAccountId(a[0].id);
        loadMoney(a[0].id).catch(() => undefined);
      }
    }).catch(() => undefined);
  }, [loadSessions, loadMoney]);

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

  async function addMoney(e: FormEvent) {
    e.preventDefault();
    if (!moneyAccountId) return;
    setBusy(true); setError(null); setInfo(null);
    try {
      const amount = Number(moneyAmount);
      await api(`/accounts/${moneyAccountId}/${moneyKind === "deposit" ? "deposits" : "withdrawals"}`, {
        method: "POST",
        body: JSON.stringify({ amount, note: moneyNote }),
      });
      setMoneyAmount(""); setMoneyNote("");
      setInfo("Mutasi dana tersimpan.");
      await loadMoney(moneyAccountId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan mutasi");
    } finally { setBusy(false); }
  }

  async function emailReport() {
    if (!activeAccount) return;
    setBusy(true); setError(null); setInfo(null);
    try {
      await api(`/accounts/${activeAccount.id}/reports/monthly/email`, {
        method: "POST",
        body: JSON.stringify({ month: reportMonth }),
      });
      setInfo("Laporan dikirim ke email Anda (dev: cek log server).");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal mengirim laporan");
    } finally { setBusy(false); }
  }

  async function removeMoney(kind: string, id: number) {
    if (!window.confirm("Hapus mutasi ini?")) return;
    try {
      await api(`/money/${kind}/${id}`, { method: "DELETE" });
      if (moneyAccountId) await loadMoney(moneyAccountId);
    } catch (err) { setError(err instanceof ApiError ? err.message : "Gagal menghapus"); }
  }

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
          <>
          <div className="row">
            <a className="btn btn-secondary" href={`/api/v1/accounts/${activeAccount.id}/export/trades.csv`} download>
              Trade (CSV)
            </a>
            <a className="btn btn-secondary" href={`/api/v1/accounts/${activeAccount.id}/export/journal.csv`} download>
              Jurnal (CSV)
            </a>
            <a className="btn btn-secondary" href={`/api/v1/accounts/${activeAccount.id}/export/excel.xlsx`} download>
              Excel (xlsx)
            </a>
          </div>
          <div className="row">
            <a className="btn btn-secondary" href={`/api/v1/accounts/${activeAccount.id}/reports/monthly.pdf`} download>
              Laporan Bulanan (PDF)
            </a>
            <input type="month" value={reportMonth} onChange={(e) => setReportMonth(e.target.value)} aria-label="Bulan laporan" />
            <button className="btn btn-secondary" onClick={emailReport} disabled={busy || !activeAccount}>
              {busy && <span className="spinner" aria-hidden="true" />}
              Kirim Email
            </button>
          </div>
          </>
        )}
      </div>

      <div className="card">
        <h2 className="title">Mutasi Dana</h2>
        <div className="row">
          <select value={moneyAccountId ?? ""} onChange={(e) => { setMoneyAccountId(Number(e.target.value)); loadMoney(Number(e.target.value)); }} aria-label="Akun mutasi">
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
          {money && (
            <span className="muted note">
              Net {money.net_deposits.toLocaleString("id-ID", { maximumFractionDigits: 2 })} · 
              Deposit {money.total_deposits.toLocaleString("id-ID", { maximumFractionDigits: 2 })} · 
              Tarik {money.total_withdrawals.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
            </span>
          )}
        </div>
        <form className="row" onSubmit={addMoney}>
          <select value={moneyKind} onChange={(e) => setMoneyKind(e.target.value as "deposit" | "withdrawal")} aria-label="Jenis mutasi">
            <option value="deposit">Deposit</option>
            <option value="withdrawal">Penarikan</option>
          </select>
          <input type="number" min="0.01" step="0.01" placeholder="Jumlah" value={moneyAmount} onChange={(e) => setMoneyAmount(e.target.value)} required />
          <input placeholder="Catatan (opsional)" value={moneyNote} onChange={(e) => setMoneyNote(e.target.value)} />
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy && <span className="spinner" aria-hidden="true" />}
            Tambah
          </button>
        </form>
        {money && money.items.length > 0 && (
          <table className="table">
            <thead><tr><th>Tanggal</th><th>Jenis</th><th>Jumlah</th><th>Metode</th><th>Catatan</th><th></th></tr></thead>
            <tbody>
              {money.items.map((m) => (
                <tr key={`${m.kind}-${m.id}`}>
                  <td>{new Date(m.ts).toLocaleDateString("id-ID")}</td>
                  <td><span className={`chip ${m.kind === "deposit" ? "chip-win" : "chip-loss"}`}>{m.kind}</span></td>
                  <td className={m.kind === "deposit" ? "pos" : "neg"}>{m.amount.toLocaleString("id-ID", { maximumFractionDigits: 2 })}</td>
                  <td>{m.method}</td>
                  <td>{m.note}</td>
                  <td><button className="btn btn-ghost" onClick={() => removeMoney(m.kind, m.id)}>Hapus</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
