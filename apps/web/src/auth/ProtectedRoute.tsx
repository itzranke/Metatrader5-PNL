import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <main className="page">
        <span className="spinner" aria-hidden="true" />
        <p className="muted">Memuat…</p>
      </main>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
