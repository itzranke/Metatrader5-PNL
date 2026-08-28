import { Link } from "react-router-dom";

export function AppShell() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">MT5 Journal</div>
        <nav>
          <Link to="/app">Dashboard</Link>
          <span className="nav-placeholder">Trading · Jurnal · Analitik (fase berikutnya)</span>
        </nav>
      </aside>
      <section className="content">
        <h1 className="title">Dashboard</h1>
        <p className="muted">Konten dashboard hadir di Phase 6. API: {import.meta.env.VITE_API_BASE ?? "/api/v1"}</p>
      </section>
    </div>
  );
}
