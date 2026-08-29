import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError } from "../lib/api";

interface Account { id: number; name: string; login: string; server: string; kind: string; currency: string; }
interface MaeItem {
  trade_id: number; ticket: string; symbol: string; side: string;
  close_time: string; net_profit: number;
  mae_pts: number | null; mfe_pts: number | null;
  mae_currency: number | null; mfe_currency: number | null;
  mae_pct: number | null; mfe_pct: number | null;
  mae_r: number | null; mfe_r: number | null;
  path_source: string; samples: number;
}
interface MaeSummary {
  covered: number;
  avg_mae_pct: number | null; avg_mfe_pct: number | null;
  avg_mae_r: number | null; avg_mfe_r: number | null;
  ratio_mae_mfe: number | null;
  source_counts: Record<string, number>;
  buckets_mae: { bucket: string; count: number }[];
  buckets_mfe: { bucket: string; count: number }[];
}
interface MaeBody { items: MaeItem[]; summary: MaeSummary; }

const fmt = (v: number | null | undefined, digits = 3) =>
  v === null || v === undefined ? "—" : v.toLocaleString("id-ID", { maximumFractionDigits: digits });

const SRC_LABEL: Record<string, string> = { ticks: "ticks", candles: "candles", none: "tanpa data" };

export function AnalyticsMaeMfePage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [body, setBody] = useState<MaeBody | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Account[]>("/accounts")
      .then((a) => {
        setAccounts(a);
        if (a.length > 0) setAccountId(a[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat akun"));
  }, []);

  const load = useCallback(async () => {
    if (accountId === null) return;
    setBusy(true); setError(null);
    try {
      setBody(await api<MaeBody>(`/accounts/${accountId}/analytics/mae-mfe`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal memuat analisis MAE/MFE");
    } finally { setBusy(false); }
  }, [accountId]);

  useEffect(() => { load().catch(() => undefined); }, [load]);

  const s = body?.summary;
  const scatter = (body?.items ?? [])
    .filter((i) => i.mae_pct !== null && i.mfe_pct !== null)
    .map((i) => ({ x: i.mae_pct as number, y: i.mfe_pct as number, win: i.net_profit >= 0 }));
  const recent = (body?.items ?? []).slice(0, 15);

  return (
    <div className="stack">
      <div className="row">
        <select value={accountId ?? ""} onChange={(e) => setAccountId(Number(e.target.value))} aria-label="Pilih akun">
          {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <h1 className="title" style={{ margin: 0 }}>MAE/MFE — Kualitas Entry & Exit</h1>
        {busy && <span className="spinner" aria-hidden="true" />}
      </div>

      {error && <div className="alert">{error}</div>}
      {!body && !error && <p className="muted">Memuat…</p>}

      {s && (
        <>
          <div className="kpi-grid">
            <div className="card kpi">
              <span className="muted">Cakupan data</span>
              <b>{s.covered} trade</b>
              <span className="muted note">
                ticks {s.source_counts.ticks} · candles {s.source_counts.candles} · tanpa {s.source_counts.none}
              </span>
            </div>
            <div className="card kpi">
              <span className="muted">MAE rata-rata</span>
              <b className="neg">{s.avg_mae_pct === null ? "—" : `${fmt(s.avg_mae_pct)}%`}</b>
              <span className="muted note">{s.avg_mae_r === null ? "" : `${fmt(s.avg_mae_r, 2)}R`}</span>
            </div>
            <div className="card kpi">
              <span className="muted">MFE rata-rata</span>
              <b className="pos">{s.avg_mfe_pct === null ? "—" : `${fmt(s.avg_mfe_pct)}%`}</b>
              <span className="muted note">{s.avg_mfe_r === null ? "" : `${fmt(s.avg_mfe_r, 2)}R`}</span>
            </div>
            <div className="card kpi">
              <span className="muted">Rasio MAE/MFE</span>
              <b>{s.ratio_mae_mfe === null ? "—" : fmt(s.ratio_mae_mfe)}</b>
              <span className="muted note">makin kecil makin baik</span>
            </div>
          </div>

          <div className="row" style={{ alignItems: "stretch" }}>
            <div className="card" style={{ flex: 2 }}>
              <h2 className="title">Scatter MAE vs MFE (% harga)</h2>
              <p className="muted note">Kiri-atas = ideal (MAE kecil, MFE besar). Hijau = win, merah = loss.</p>
              {scatter.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis type="number" dataKey="x" name="MAE %" stroke="var(--color-muted)" tick={{ fontSize: 11 }} />
                    <YAxis type="number" dataKey="y" name="MFE %" stroke="var(--color-muted)" tick={{ fontSize: 11 }} />
                    <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v: number, name: string) => [`${fmt(v)}%`, name === "x" ? "MAE" : "MFE"]} />
                    <Scatter data={scatter} fill="var(--color-primary)">
                      {scatter.map((p, i) => <Cell key={i} fill={p.win ? "var(--color-win)" : "var(--color-loss)"} />)}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              ) : (
                <p className="muted">Belum ada data MAE/MFE.</p>
              )}
            </div>

            <div className="card" style={{ flex: 1 }}>
              <h2 className="title">Distribusi</h2>
              <div className="row">
                <div className="stack" style={{ flex: 1 }}>
                  <span className="muted note">MAE</span>
                  {s.buckets_mae.map((b) => (
                    <div key={b.bucket} className="score-row">
                      <span className="muted note score-name">{b.bucket}</span>
                      <div className="score-track">
                        <div className="score-fill" style={{ width: `${Math.min(100, (b.count / Math.max(1, s.covered)) * 100 * 3)}%` }} />
                      </div>
                      <span className="muted note">{b.count}</span>
                    </div>
                  ))}
                </div>
                <div className="stack" style={{ flex: 1 }}>
                  <span className="muted note">MFE</span>
                  {s.buckets_mfe.map((b) => (
                    <div key={b.bucket} className="score-row">
                      <span className="muted note score-name">{b.bucket}</span>
                      <div className="score-track">
                        <div className="score-fill" style={{ width: `${Math.min(100, (b.count / Math.max(1, s.covered)) * 100 * 3)}%` }} />
                      </div>
                      <span className="muted note">{b.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 className="title">Trade terbaru</h2>
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>Simbol</th><th>Side</th><th>Hasil</th>
                    <th>MAE pts</th><th>MFE pts</th><th>MAE %</th><th>MFE %</th><th>MAE R</th><th>MFE R</th><th>Sumber</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((i) => (
                    <tr key={i.trade_id}>
                      <td>{i.symbol}</td>
                      <td>{i.side}</td>
                      <td className={i.net_profit >= 0 ? "pos" : "neg"}>{fmt(i.net_profit)}</td>
                      <td>{fmt(i.mae_pts)}</td>
                      <td>{fmt(i.mfe_pts)}</td>
                      <td>{fmt(i.mae_pct)}%</td>
                      <td>{fmt(i.mfe_pct)}%</td>
                      <td>{fmt(i.mae_r)}R</td>
                      <td>{fmt(i.mfe_r)}R</td>
                      <td>
                        <span className={`chip ${i.path_source === "ticks" ? "chip-win" : i.path_source === "candles" ? "chip-warn" : "chip-loss"}`}>
                          {SRC_LABEL[i.path_source] ?? i.path_source}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
