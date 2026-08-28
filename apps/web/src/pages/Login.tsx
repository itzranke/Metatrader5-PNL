import { Link } from "react-router-dom";

export function Login({ register = false }: { register?: boolean }) {
  return (
    <main className="page">
      <h1 className="display">{register ? "Daftar" : "Masuk"}</h1>
      <p className="muted">
        Form autentikasi tersedia di Phase 2 (Authentication). {register ? "" : "Kembali ke "}
        {!register && <Link to="/">beranda</Link>}
      </p>
    </main>
  );
}
