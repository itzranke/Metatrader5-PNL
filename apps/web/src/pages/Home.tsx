import { Link } from "react-router-dom";

export function Home() {
  return (
    <main className="page">
      <h1 className="display">MT5 Journal</h1>
      <p className="muted">
        Jurnal trading MT5: sinkronisasi otomatis, analitik, insight, dan laporan.
      </p>
      <div className="row">
        <Link className="btn btn-primary" to="/register">
          Daftar Gratis
        </Link>
        <Link className="btn btn-secondary" to="/login">
          Masuk
        </Link>
      </div>
    </main>
  );
}
