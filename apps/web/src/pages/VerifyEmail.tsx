import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

export function VerifyEmail() {
  const [params] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    const token = params.get("token") ?? "";
    (async () => {
      try {
        await api("/auth/verify", { method: "POST", body: JSON.stringify({ token }) });
        setStatus("ok");
      } catch {
        setStatus("error");
      }
    })();
  }, [params]);

  return (
    <main className="page auth-page">
      <h1 className="display">
        {status === "loading" && "Memverifikasi…"}
        {status === "ok" && "Email Terverifikasi"}
        {status === "error" && "Link Tidak Valid"}
      </h1>
      {status === "ok" && (
        <>
          <p className="muted">Akun kamu sudah aktif sepenuhnya. Selamat berjurnal!</p>
          <Link className="btn btn-primary" to="/login">
            Masuk
          </Link>
        </>
      )}
      {status === "error" && (
        <>
          <p className="muted">Token verifikasi tidak valid atau sudah kedaluwarsa (24 jam).</p>
          <Link className="btn btn-secondary" to="/login">
            Kembali ke Masuk
          </Link>
        </>
      )}
    </main>
  );
}
