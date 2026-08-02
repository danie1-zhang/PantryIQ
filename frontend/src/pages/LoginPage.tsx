import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("developer@example.com");
  const [password, setPassword] = useState("development");
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  function submit(event: FormEvent) {
    event.preventDefault();
    login();
    const target =
      (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/dashboard";
    navigate(target, { replace: true });
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
          <p className="eyebrow">Development access</p>
          <h2>Welcome back</h2>
          <p className="muted">
            Authentication is coming next. For now, continue with the seeded development profile.
          </p>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              required
            />
          </div>
          <button className="button button-primary button-large">Continue to dashboard</button>
          <p className="development-note">
            Local development only · No credentials are sent to the API
          </p>
        </form>
      </section>
    </main>
  );
}
