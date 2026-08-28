import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/auth/forgot", { method: "POST", body: JSON.stringify({ email }) });
      setSent(true);
    } catch {
      setError("Terjadi kesalahan. Coba lagi.");
    }
  }

  if (sent) {
    return (
      <main className="page auth-page">
        <h1 className="display">Cek email kamu</h1>
        <p className="muted">
          Jika email terdaftar, link reset password sudah dikirim (berlaku 15 menit). Periksa
          folder spam juga ya.
        </p>
        <Link className="btn btn-secondary" to="/login">
          Kembali ke Masuk
        </Link>
      </main>
    );
  }

  return (
    <main className="page auth-page">
      <h1 className="display">Lupa Password</h1>
      <form className="card form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" type="submit">
          Kirim Link Reset
        </button>
      </form>
      <Link className="muted" to="/login">
        Kembali ke Masuk
      </Link>
    </main>
  );
}
