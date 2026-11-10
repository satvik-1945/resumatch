"use client";
import { useState, type FormEvent } from "react";
import { api, type User } from "@/lib/api";

export function Auth({ onLogin }: { onLogin: (user: User) => void }) {
  const [register, setRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const f = new FormData(event.currentTarget);
    try { onLogin(await api<User>(register ? "/auth/register" : "/auth/login", "POST", {
      email: f.get("email"), password: f.get("password"),
    })); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <div className="welcome"><section><p className="eyebrow">SMALL SESSIONS. REAL CONNECTIONS.</p>
    <h1>Show up.<br />Reach out.<br /><em>Keep going.</em></h1>
    <p className="lede">A private space for the work behind your next opportunity. Capture your research and outreach, review it, and see your progress.</p>
    <div className="steps"><span>01 · Start a session</span><span>02 · Capture as you go</span><span>03 · Review & reflect</span></div>
  </section><section className="panel auth"><p className="eyebrow">YOUR PERSONAL WORKSPACE</p>
    <h2>{register ? "A fresh start" : "Welcome back"}</h2><p className="muted">{register ? "Create an account. Your first session is one step away." : "Sign in and pick up your next good conversation."}</p>
    <form onSubmit={submit}><label>Email<input name="email" type="email" required autoComplete="email" /></label>
      <label>Password<input name="password" type="password" required minLength={12} maxLength={128} autoComplete={register ? "new-password" : "current-password"} /></label>
      <p className="hint">12–128 characters. Local accounts; password recovery is not available yet.</p>
      {error && <p role="alert" className="error">{error}</p>}
      <button className="primary" disabled={busy}>{busy ? "One moment…" : register ? "Create account" : "Sign in"}</button>
    </form><button className="text-button" disabled={busy} onClick={() => { setRegister(!register); setError(""); }}>{register ? "Already have an account? Sign in" : "New here? Create an account"}</button>
    <p className="hint">The previous résumé workspace was reset. Create a new account to begin.</p>
  </section></div>;
}
