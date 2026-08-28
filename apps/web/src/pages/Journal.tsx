import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../lib/api";

interface Account { id: number; name: string; kind: string; login: string; }
interface TradeOption { id: number; symbol: string; side: string; net_profit: number; close_time: string; }
interface JournalEntry {
  id: number; trading_account_id: number; trade_id: number | null;
  entry_date: string; setup: string;
  emotion_before: string; emotion_during: string; emotion_after: string;
  confidence: number; discipline: number;
  fear: boolean; greed: boolean; revenge: boolean; fomo: boolean; boredom: boolean;
  reason_entry: string; reason_exit: string; notes: string; lesson: string;
  plan_match: boolean | null; screenshot_path: string | null;
  tags: string[]; trade_symbol: string | null; trade_net_profit: number | null;
}
interface Tag { id: number; name: string; color: string; }

const EMOTIONS = ["calm", "confident", "anxious", "greedy", "fearful", "neutral", "frustrated"];
const SETUPS = ["Breakout", "Retest", "News", "Trend", "Reversal", "Rejection", "Range", ""];
const fmtMoney = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${v.toLocaleString("id-ID", { maximumFractionDigits: 2 })}`;

const EMPTY_FORM = {
  trading_account_id: 0, trade_id: "", setup: "", emotion_before: "calm",
  emotion_during: "calm", emotion_after: "calm", confidence: 3, discipline: 3,
  notes: "", tags: "", reason_entry: "", reason_exit: "", lesson: "",
  fear: false, greed: false, revenge: false, fomo: false, boredom: false,
};

export function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [trades, setTrades] = useState<TradeOption[]>([]);
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [filterTag, setFilterTag] = useState("");
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadEntries = useCallback(async () => {
    const q = filterTag ? `?tag=${encodeURIComponent(filterTag)}` : "";
    setEntries(await api<JournalEntry[]>(`/journal${q}`));
  }, [filterTag]);

  useEffect(() => {
    api<Account[]>("/accounts").then((a) => {
      setAccounts(a);
      if (a.length > 0) setForm((f) => ({ ...f, trading_account_id: f.trading_account_id || a[0].id }));
    }).catch((e) => setError(e instanceof Error ? e.message : "Gagal memuat akun"));
    api<Tag[]>("/tags").then(setTags).catch(() => undefined);
  }, []);

  useEffect(() => { loadEntries().catch((e) => setError(e.message)); }, [loadEntries]);

  async function loadTrades(accountId: number) {
    if (!accountId) return;
    const r = await api<{ items: TradeOption[] }>(`/accounts/${accountId}/trades?limit=50`);
    setTrades(r.items);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setInfo(null);
    try {
      const payload = {
        ...form,
        trading_account_id: Number(form.trading_account_id),
        trade_id: form.trade_id ? Number(form.trade_id) : null,
        tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
        entry_date: new Date().toISOString(),
      };
      if (editingId === null) {
        await api("/journal", { method: "POST", body: JSON.stringify(payload) });
        setInfo("Jurnal tersimpan.");
      } else {
        await api(`/journal/${editingId}`, { method: "PATCH", body: JSON.stringify(payload) });
        setInfo("Jurnal diperbarui.");
      }
      if (screenshotFile && fileRef.current) {
        const fd = new FormData();
        fd.append("file", screenshotFile);
        const target = editingId ?? (await api<JournalEntry[]>("/journal"))[0]?.id;
        if (target) await api(`/journal/${target}/screenshot`, { method: "POST", body: fd });
      }
      setForm({ ...EMPTY_FORM, trading_account_id: Number(form.trading_account_id) });
      setEditingId(null); setScreenshotFile(null);
      if (fileRef.current) fileRef.current.value = "";
      await loadEntries();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gagal menyimpan jurnal");
    } finally { setBusy(false); }
  }

  function edit(e: JournalEntry) {
    setEditingId(e.id);
    setForm({
      trading_account_id: e.trading_account_id, trade_id: e.trade_id ? String(e.trade_id) : "",
      setup: e.setup, emotion_before: e.emotion_before, emotion_during: e.emotion_during,
      emotion_after: e.emotion_after, confidence: e.confidence, discipline: e.discipline,
      notes: e.notes, tags: e.tags.join(", "), reason_entry: e.reason_entry,
      reason_exit: e.reason_exit, lesson: e.lesson,
      fear: e.fear, greed: e.greed, revenge: e.revenge, fomo: e.fomo, boredom: e.boredom,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remove(id: number) {
    if (!window.confirm("Hapus entri jurnal ini?")) return;
    try {
      await api(`/journal/${id}`, { method: "DELETE" });
      await loadEntries();
    } catch (err) { setError(err instanceof ApiError ? err.message : "Gagal menghapus"); }
  }

  const set = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div>
      <h1 className="title">Jurnal Trading</h1>
      <p className="muted">Catat setup, emosi, dan pelajaran untuk setiap trade.</p>
      {error && <p className="error" role="alert">{error}</p>}
      {info && <p className="info" role="status">{info}</p>}

      <form className="card form" onSubmit={submit}>
        <h2 className="title">{editingId === null ? "Entri Baru" : `Edit Entri #${editingId}`}</h2>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="j-acc">Akun</label>
            <select id="j-acc" value={form.trading_account_id} onChange={(e) => { set("trading_account_id", Number(e.target.value)); loadTrades(Number(e.target.value)); }}>
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="j-trade">Trade (opsional)</label>
            <select id="j-trade" value={form.trade_id} onChange={(e) => set("trade_id", e.target.value)}>
              <option value="">Tanpa trade (manual)</option>
              {trades.map((t) => (
                <option key={t.id} value={t.id}>
                  {new Date(t.close_time).toLocaleDateString("id-ID")} {t.symbol} {t.side.toUpperCase()} {fmtMoney(t.net_profit)}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="j-setup">Setup</label>
            <select id="j-setup" value={form.setup} onChange={(e) => set("setup", e.target.value)}>
              {SETUPS.map((s) => <option key={s || "none"} value={s}>{s || "(kosong)"}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="j-conf">Confidence (1–5)</label>
            <input id="j-conf" type="number" min={1} max={5} value={form.confidence} onChange={(e) => set("confidence", Number(e.target.value))} />
          </div>
          <div className="field">
            <label htmlFor="j-disc">Discipline (1–5)</label>
            <input id="j-disc" type="number" min={1} max={5} value={form.discipline} onChange={(e) => set("discipline", Number(e.target.value))} />
          </div>
          <div className="field">
            <label>Emosi (sebelum / saat / sesudah)</label>
            <div className="row">
              {(["emotion_before", "emotion_during", "emotion_after"] as const).map((k) => (
                <select key={k} value={String(form[k])} onChange={(e) => set(k, e.target.value)} aria-label={k}>
                  {EMOTIONS.map((em) => <option key={em} value={em}>{em}</option>)}
                </select>
              ))}
            </div>
          </div>
        </div>
        <div className="form-grid">
          {(["fear", "greed", "revenge", "fomo", "boredom"] as const).map((flag) => (
            <label key={flag} className="check">
              <input type="checkbox" checked={Boolean(form[flag])} onChange={(e) => set(flag, e.target.checked)} />
              {flag}
            </label>
          ))}
        </div>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="j-re">Alasan Entry</label>
            <input id="j-re" value={form.reason_entry} onChange={(e) => set("reason_entry", e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="j-rx">Alasan Exit</label>
            <input id="j-rx" value={form.reason_exit} onChange={(e) => set("reason_exit", e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="j-tags">Tag (pisah koma)</label>
            <input id="j-tags" value={form.tags} onChange={(e) => set("tags", e.target.value)} placeholder="breakout, harian" />
          </div>
          <div className="field">
            <label htmlFor="j-lesson">Pelajaran</label>
            <input id="j-lesson" value={form.lesson} onChange={(e) => set("lesson", e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label htmlFor="j-notes">Catatan</label>
          <textarea id="j-notes" rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="j-shot">Screenshot chart</label>
          <input id="j-shot" ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setScreenshotFile(e.target.files?.[0] ?? null)} />
        </div>
        <div className="row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy && <span className="spinner" aria-hidden="true" />}
            {editingId === null ? "Simpan Jurnal" : "Perbarui Jurnal"}
          </button>
          {editingId !== null && (
            <button className="btn btn-ghost" type="button" onClick={() => { setEditingId(null); setForm({ ...EMPTY_FORM, trading_account_id: Number(form.trading_account_id) }); }}>
              Batal
            </button>
          )}
        </div>
      </form>

      <div className="row spread dash-top">
        <h2 className="title">Semua Entri ({entries.length})</h2>
        <select value={filterTag} onChange={(e) => setFilterTag(e.target.value)} aria-label="Filter tag">
          <option value="">Semua tag</option>
          {tags.map((t) => <option key={t.id} value={t.name}>{t.name}</option>)}
        </select>
      </div>

      {entries.length === 0 ? (
        <div className="card empty"><span className="title">Belum ada jurnal</span></div>
      ) : (
        <div className="journal-list">
          {entries.map((e) => (
            <article className="card" key={e.id}>
              <div className="row spread">
                <b>{e.trade_symbol ? `${e.trade_symbol} ${e.trade_net_profit !== null ? fmtMoney(e.trade_net_profit) : ""}` : "Manual entry"}</b>
                <span className="muted note">{new Date(e.entry_date).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })}</span>
              </div>
              <div className="row">
                {e.setup && <span className="chip">{e.setup}</span>}
                <span className="chip">{e.emotion_before} → {e.emotion_during} → {e.emotion_after}</span>
                <span className="chip">conf {e.confidence}/5 · disc {e.discipline}/5</span>
                {e.tags.map((t) => <span className="chip" key={t} style={{ borderColor: "var(--color-primary)" }}>{t}</span>)}
              </div>
              {e.notes && <p className="muted note">{e.notes}</p>}
              {(e.reason_entry || e.reason_exit || e.lesson) && (
                <p className="muted note">
                  {e.reason_entry && <b>Entry:</b>} {e.reason_entry}{e.reason_entry && " · "}
                  {e.reason_exit && <b>Exit:</b>} {e.reason_exit}{e.reason_exit && " · "}
                  {e.lesson && <b>Lesson:</b>} {e.lesson}
                </p>
              )}
              {e.screenshot_path && (
                <img src={`/uploads/${e.screenshot_path}`} alt="Screenshot chart" className="journal-shot" loading="lazy" />
              )}
              <div className="row">
                <button className="btn btn-ghost" onClick={() => edit(e)}>Edit</button>
                <button className="btn btn-ghost" onClick={() => remove(e.id)}>Hapus</button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
