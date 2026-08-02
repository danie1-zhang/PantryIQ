import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/auth";
import { errorMessage } from "../api/client";

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    username: "",
    name: "",
    password: "",
    confirm: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (form.password !== form.confirm) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      await register({
        email: form.email,
        username: form.username,
        name: form.name,
        password: form.password,
      });
      navigate("/login", {
        replace: true,
        state: { message: "Account created. You can now log in." },
      });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <main className="login-page">
      <section className="login-visual">
        <div className="brand brand-light">
          <span className="brand-mark">P</span>
          <span>PantryIQ</span>
        </div>
        <div>
          <p className="eyebrow">Start with your pantry</p>
          <h1>Create your account.</h1>
          <p>Your inventory and meal history stay scoped to you.</p>
        </div>
      </section>
      <section className="login-panel">
        <form className="login-form" onSubmit={submit}>
          <p className="eyebrow">Registration</p>
          <h2>Join PantryIQ</h2>
          {error && (
            <div className="state-panel state-error" role="alert">
              {error}
            </div>
          )}
          <div className="field">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              autoComplete="name"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              autoComplete="username"
              minLength={3}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              autoComplete="new-password"
              minLength={12}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="confirm">Confirm password</label>
            <input
              id="confirm"
              type="password"
              value={form.confirm}
              onChange={(e) => update("confirm", e.target.value)}
              autoComplete="new-password"
              minLength={12}
              required
            />
          </div>
          <button className="button button-primary button-large" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
          <p className="development-note">
            Already registered? <Link to="/login">Log in</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
