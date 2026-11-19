import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errText } from "../api";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault(); setErr(""); setMsg("");
    try { setMsg((await api("/auth/password-reset/", { method: "POST", body: { email } })).detail); } catch (ex) { setErr(errText(ex)); }
  }
  return (
    <form onSubmit={submit} className="card mx-auto max-w-sm space-y-3 p-6">
      <h1 className="text-xl font-bold">Forgot password? 🔑</h1>
      <p className="text-sm text-slate-500">Enter your email and we'll send you a reset link.</p>
      <input className="input" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
      {msg && <p className="ok">{msg}</p>}
      {err && <p className="err">{err}</p>}
      <button className="btn w-full">Send reset link</button>
      <Link to="/login" className="block text-center text-sm font-medium text-indigo-600">Back to log in</Link>
    </form>
  );
}

export function ResetPassword() {
  const { uid, token } = useParams();
  const nav = useNavigate();
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  async function submit(e) {
    e.preventDefault(); setErr("");
    try {
      await api("/auth/password-reset/confirm/", { method: "POST", body: { uid, token, password: pw } });
      setDone(true); setTimeout(() => nav("/login"), 1500);
    } catch (ex) { setErr(errText(ex)); }
  }
  return (
    <form onSubmit={submit} className="card mx-auto max-w-sm space-y-3 p-6">
      <h1 className="text-xl font-bold">Choose a new password</h1>
      <input className="input" type="password" placeholder="New password (min 8)" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" required />
      {err && <p className="err">{err}</p>}
      {done && <p className="ok">Password updated! Redirecting to log in…</p>}
      <button className="btn w-full" disabled={done}>Update password</button>
    </form>
  );
}
