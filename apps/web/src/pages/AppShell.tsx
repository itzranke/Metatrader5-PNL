import { Link, Route, Routes } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { AccountsPage } from "./Accounts";
import { ConnectorPage } from "./Connector";
import { DashboardPage } from "./Dashboard";

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">MT5 Journal</div>
        <nav>
          <Link to="/app">Dashboard</Link>
          <Link to="/app/accounts">Akun</Link>
          <Link to="/app/connector">Connector</Link>
          <span className="nav-placeholder">Trading · Jurnal · Analitik (fase berikutnya)</span>
        </nav>
      </aside>
      <section className="content">
        <header className="topbar">
          <h1 className="title">MT5 Journal</h1>
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
        <Routes>
          <Route index element={<DashboardPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="connector" element={<ConnectorPage />} />
        </Routes>
      </section>
    </div>
  );
}
