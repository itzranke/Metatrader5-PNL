import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";

export function Login({ register = false }: { register?: boolean }) {
  const { login, register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      if (register) {
        await registerUser(username, email, password);
        setInfo("Pendaftaran berhasil. Cek email kamu untuk verifikasi (periksa folder spam).");
      } else {
        await login(email, password);
        navigate("/app", { replace: true });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Terjadi kesalahan. Coba lagi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page auth-page">
      <h1 className="display">{register ? "Daftar Gratis" : "Masuk"}</h1>
      <p className="muted">
        {register
          ? "Mulai jurnal trading MT5 kamu — gratis."
          : "Selamat datang kembali. Masuk ke akun kamu."}
      </p>

      <form className="card form" onSubmit={onSubmit}>
        {register && (
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="mis. andi_trader"
              autoComplete="username"
              required
              minLength={3}
            />
          </div>
        )}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="kamu@email.com"
            autoComplete="email"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="minimal 8 karakter"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={8}
          />
        </div>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {info && <p className="info" role="status">{info}</p>}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy && <span className="spinner" aria-hidden="true" />}
          {register ? "Daftar" : "Masuk"}
        </button>
      </form>

      <p className="muted">
        {register ? (
          <>
            Sudah punya akun? <Link to="/login">Masuk</Link>
          </>
        ) : (
          <>
            Belum punya akun? <Link to="/register">Daftar Gratis</Link> ·{" "}
            <Link to="/forgot-password">Lupa password?</Link>
          </>
        )}
      </p>
    </main>
  );
}
