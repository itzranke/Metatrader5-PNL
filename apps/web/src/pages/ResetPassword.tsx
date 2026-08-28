import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export function ResetPassword() {
  const [params] = useSearchParams();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const token = params.get("token") ?? "";
    try {
      await api("/auth/reset", { method: "POST", body: JSON.stringify({ token, password }) });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Token tidak valid atau kedaluwarsa.");
    }
  }

  if (done) {
    return (
      <main className="page auth-page">
        <h1 className="display">Password Diganti</h1>
        <p className="muted">Password kamu sudah diperbarui. Silakan masuk dengan password baru.</p>
        <Link className="btn btn-primary" to="/login">
          Masuk
        </Link>
      </main>
    );
  }

  return (
    <main className="page auth-page">
      <h1 className="display">Reset Password</h1>
      <form className="card form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="password">Password Baru</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="minimal 8 karakter"
            autoComplete="new-password"
            required
            minLength={8}
          />
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn-primary" type="submit">
          Ganti Password
        </button>
      </form>
    </main>
  );
}
