import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function AppShell() {
  const { user, logout } = useAuth();

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
        <header className="topbar">
          <h1 className="title">Dashboard</h1>
          <div className="row">
            {user && (
              <>
                <span className="chip">{user.username}</span>
                {!user.email_verified && (
                  <span className="chip chip-warn">Email belum diverifikasi</span>
                )}
                <button className="btn btn-ghost" onClick={() => logout()}>
                  Keluar
                </button>
              </>
            )}
          </div>
        </header>
        <p className="muted">
          Konten dashboard hadir di Phase 6. API: {import.meta.env.VITE_API_BASE ?? "/api/v1"}
        </p>
      </section>
    </div>
  );
}
