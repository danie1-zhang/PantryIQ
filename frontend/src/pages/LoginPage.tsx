import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login({ email_or_username: identifier, password });
      const target =
        (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";
      navigate(target, { replace: true });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-visual">
        <div className="brand brand-light">
          <span className="brand-mark">P</span>
          <span>PantryIQ</span>
        </div>
        <div>
          <p className="eyebrow">Eat well with what you have</p>
          <h1>Your pantry, turned into a plan.</h1>
          <p>Build satisfying meals around your nutrition goals—without another grocery run.</p>
        </div>
        <div className="visual-stat">
          <strong>51</strong>
          <span>curated foods ready to explore</span>
        </div>
      </section>
      <section className="login-panel">
        <form className="login-form" onSubmit={submit}>
          <p className="eyebrow">Account access</p>
          <h2>Welcome back</h2>
          <p className="muted">Log in to access your pantry and nutrition goals.</p>
          {error && (
            <div className="state-panel state-error" role="alert">
              {error}
            </div>
          )}
          <div className="field">
            <label htmlFor="identifier">Email or username</label>
            <input
              id="identifier"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoComplete="username"
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
              autoComplete="current-password"
              required
            />
          </div>
          <button className="button button-primary button-large" disabled={submitting}>
            {submitting ? "Logging in…" : "Log in"}
          </button>
          <p className="development-note">
            New to PantryIQ? <Link to="/register">Create an account</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
