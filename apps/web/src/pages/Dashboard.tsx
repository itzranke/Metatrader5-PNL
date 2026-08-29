import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError } from "../lib/api";

interface Account { id: number; name: string; login: string; server: string; kind: string; currency: string; }
interface Overview {
  account_id: number; account_name: string; currency: string; days: number;
  balance: number | null; equity: number | null; open_positions: number; floating_pnl: number;
  today_pnl: number; month_pnl: number;
  summary: {
    total_trades: number; win_count: number; loss_count: number; be_count: number;
    net_profit: number; gross_profit: number; gross_loss: number;
    win_rate: number | null; profit_factor: number | null; expectancy: number | null;
    max_drawdown: number | null; winning_streak: number; losing_streak: number;
  };
}
interface EquityPoint { ts: string; equity: number; }
interface CalendarDay { day: string; net_profit: number; trades: number; wins: number; }
interface Position { ticket: string; symbol: string; side: string; volume: number; open_time: string; floating_pnl: number | null; }
interface TradeRow { id: number; symbol: string; side: string; volume: number; net_profit: number; close_time: string; }
interface Score {
  score: number | null; progress: number; need: number; label: string | null;
  data_complete: boolean;
  components: Record<string, { weight: number; sub: number }> | null;
}

const fmt = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? "—" : v.toLocaleString("id-ID", { minimumFractionDigits: digits, maximumFractionDigits: digits });

function money(v: number | null | undefined) {
  return v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${fmt(v)}`;
}

export function DashboardPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [days, setDays] = useState<number | null>(null); // null = semua
  const [ov, setOv] = useState<Overview | null>(null);
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<TradeRow[]>([]);
  const [score, setScore] = useState<Score | null>(null);
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
    setBusy(true);
    setError(null);
    const q = days ? `?days=${days}` : "";
    try {
      const [o, eq, cal, pos, tr, sc] = await Promise.all([
        api<Overview>(`/accounts/${accountId}/overview${q}`),
        api<EquityPoint[]>(`/accounts/${accountId}/equity${q}`),
        api<CalendarDay[]>(`/accounts/${accountId}/calendar`),
        api<Position[]>(`/accounts/${accountId}/positions`),
        api<{ items: TradeRow[] }>(`/accounts/${accountId}/trades?limit=10`),
        api<Score>(`/accounts/${accountId}/score`),
      ]);
      setOv(o); setEquity(eq); setCalendar(cal); setPositions(pos); setTrades(tr.items); setScore(sc);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal memuat dashboard");
    } finally {
      setBusy(false);
    }
  }, [accountId, days]);

  useEffect(() => { load(); }, [load]);

  // kalender heatmap: grid bulan ini
  function renderCalendar() {
    const now = new Date();
    const y = now.getFullYear(), m = now.getMonth();
    const first = new Date(y, m, 1);
    const startPad = first.getDay(); // 0 = Minggu
    const totalDays = new Date(y, m + 1, 0).getDate();
    const byDay = new Map(calendar.map((d) => [d.day, d]));
    const cells: (CalendarDay | null)[] = [];
    for (let i = 0; i < startPad; i++) cells.push(null);
    for (let d = 1; d <= totalDays; d++) {
      const key = `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      cells.push(byDay.get(key) ?? null);
    }
    const maxAbs = Math.max(1, ...calendar.map((c) => Math.abs(c.net_profit)));
    return (
      <div className="calendar-grid" aria-label="Kalender P&L bulan ini">
        {cells.map((c, i) => {
          if (c === null) return <div key={i} className="cal-cell cal-empty" />;
          const ratio = Math.abs(c.net_profit) / maxAbs;
          const cls = c.net_profit > 0 ? "cal-win" : c.net_profit < 0 ? "cal-loss" : "cal-be";
          const opacity = 0.25 + 0.75 * ratio;
          return (
            <div key={i} className={`cal-cell ${cls}`} style={{ opacity }}
                 title={`${c.day}: ${money(c.net_profit)} (${c.trades} trade)`} />
          );
        })}
      </div>
    );
  }

  return (
    <div>
      <div className="row spread dash-top">
        <h1 className="title">Dashboard</h1>
        <div className="row">
          <select value={accountId ?? ""} onChange={(e) => setAccountId(Number(e.target.value))} aria-label="Pilih akun">
            {accounts.length === 0 && <option value="">Belum ada akun</option>}
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name} ({a.kind === "demo" ? "Data Contoh" : a.login})</option>
            ))}
          </select>
          <select value={days ?? "all"} onChange={(e) => setDays(e.target.value === "all" ? null : Number(e.target.value))} aria-label="Rentang waktu">
            <option value={7}>7 hari</option>
            <option value={30}>30 hari</option>
            <option value={90}>90 hari</option>
            <option value="all">Semua</option>
          </select>
          {busy && <span className="spinner" aria-hidden="true" />}
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {accounts.length === 0 && !error && (
        <div className="card empty">
          <span className="title">Belum ada akun</span>
          <span className="muted">Buat "Data Contoh" di halaman Akun untuk melihat dashboard.</span>
        </div>
      )}

      {ov && (
        <>
          <div className="kpi-grid">
            <div className="card kpi"><span className="muted">P&L Hari Ini</span><b className={ov.today_pnl >= 0 ? "pos" : "neg"}>{money(ov.today_pnl)}</b></div>
            <div className="card kpi"><span className="muted">P&L Bulan Ini</span><b className={ov.month_pnl >= 0 ? "pos" : "neg"}>{money(ov.month_pnl)}</b></div>
            <div className="card kpi"><span className="muted">Win Rate</span><b>{ov.summary.win_rate === null ? "—" : `${fmt(ov.summary.win_rate, 1)}%`}</b></div>
            <div className="card kpi"><span className="muted">Profit Factor</span><b>{fmt(ov.summary.profit_factor)}</b></div>
            <div className="card kpi"><span className="muted">Expectancy</span><b className={ov.summary.expectancy !== null && ov.summary.expectancy >= 0 ? "pos" : "neg"}>{money(ov.summary.expectancy)}</b></div>
            <div className="card kpi"><span className="muted">Max Drawdown</span><b className="neg">{money(ov.summary.max_drawdown)}</b></div>
            <div className="card kpi">
              <span className="muted">Skor Performa {!score?.data_complete && score?.score !== null && <span className="chip chip-warn">{"jurnal < 10"}</span>}</span>
              <b>{score?.score === null || !score ? (score ? `${score.progress}/${score.need} trade` : "—") : `${score.score} · ${score.label}`}</b>
            </div>
          </div>

          {score?.components && (
            <div className="card">
              <h2 className="title">Komponen Skor</h2>
              <div className="score-bars">
                {Object.entries(score.components).map(([key, c]) => (
                  <div key={key} className="score-row">
                    <span className="muted note score-name">{key.replace("_", " ")} ({c.weight})</span>
                    <div className="score-track"><div className="score-fill" style={{ width: `${Math.round(c.sub * 100)}%` }} /></div>
                    <span className="muted note">{Math.round(c.sub * 100)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card">
            <div className="row spread">
              <h2 className="title">Equity Curve</h2>
              <span className="muted note">
                {ov.balance !== null ? `Balance ${fmt(ov.balance)} ${ov.currency}` : "P&L kumulatif"}
              </span>
            </div>
            {equity.length === 0 ? (
              <p className="muted">Belum ada data equity.</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={equity} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="ts" tickFormatter={(v: string) => v.slice(0, 10)} fontSize={11} stroke="var(--color-muted)" />
                  <YAxis width={70} fontSize={11} stroke="var(--color-muted)" />
                  <Tooltip
                    formatter={(v: number) => [fmt(v), "Equity"]}
                    labelFormatter={(l: string) => l.slice(0, 10)}
                    contentStyle={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: 8 }}
                  />
                  <Line type="monotone" dataKey="equity" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid-2">
            <div className="card">
              <h2 className="title">P&L Kalender — Bulan Ini</h2>
              {renderCalendar()}
              <p className="muted note">Hijau = profit, merah = rugi. Klik hari untuk detail (fase jurnal).</p>
            </div>
            <div className="card">
              <h2 className="title">Posisi Terbuka ({positions.length})</h2>
              {positions.length === 0 ? (
                <p className="muted">Tidak ada posisi terbuka.</p>
              ) : (
                <table className="table">
                  <thead><tr><th>Simbol</th><th>Arah</th><th>Vol</th><th>P&L</th></tr></thead>
                  <tbody>
                    {positions.map((p) => (
                      <tr key={p.ticket}>
                        <td>{p.symbol}</td>
                        <td><span className={`chip ${p.side === "buy" ? "chip-win" : "chip-loss"}`}>{p.side.toUpperCase()}</span></td>
                        <td>{p.volume}</td>
                        <td className={p.floating_pnl !== null && p.floating_pnl >= 0 ? "pos" : "neg"}>{money(p.floating_pnl)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div className="card">
            <h2 className="title">Trade Terbaru</h2>
            {trades.length === 0 ? (
              <p className="muted">Belum ada trade.</p>
            ) : (
              <table className="table">
                <thead><tr><th>Waktu</th><th>Simbol</th><th>Arah</th><th>Vol</th><th>Net P&L</th></tr></thead>
                <tbody>
                  {trades.map((t) => (
                    <tr key={t.id}>
                      <td>{new Date(t.close_time).toLocaleString("id-ID", { dateStyle: "short", timeStyle: "short" })}</td>
                      <td>{t.symbol}</td>
                      <td><span className={`chip ${t.side === "buy" ? "chip-win" : "chip-loss"}`}>{t.side.toUpperCase()}</span></td>
                      <td>{t.volume}</td>
                      <td className={t.net_profit >= 0 ? "pos" : "neg"}>{money(t.net_profit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
