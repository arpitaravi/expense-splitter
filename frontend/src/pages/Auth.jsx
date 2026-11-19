import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { errText, login, register } from "../api";

const POINTS = [
  ["🧮", "Smart splits", "Equal, exact, percentage or shares"],
  ["🔀", "Fewest payments", "Debts simplified automatically"],
  ["🔁", "Recurring bills", "Rent & wifi added on their own"],
];

export default function Auth({ mode }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [f, setF] = useState({ username: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function go(fn) {
    setErr(""); setBusy(true);
    try { await fn(); qc.clear(); nav("/"); } catch (ex) { setErr(errText(ex)); } finally { setBusy(false); }
  }
  const submit = (e) => {
    e.preventDefault();
    go(() => (mode === "login" ? login(f.username, f.password) : register(f.username, f.email, f.password)));
  };

  return (
    <div className="grid items-center gap-6 md:grid-cols-2">
      <div className="space-y-4 px-2">
        <h1 className="text-3xl font-extrabold leading-tight text-slate-800 sm:text-4xl">
          Split bills with friends,<br /><span className="bg-gradient-to-r from-indigo-600 to-fuchsia-600 bg-clip-text text-transparent">without the awkward maths.</span>
        </h1>
        <ul className="space-y-3">
          {POINTS.map(([e, t, d]) => (
            <li key={t} className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-xl shadow">{e}</span>
              <span><b className="block text-sm">{t}</b><span className="text-sm text-slate-500">{d}</span></span>
            </li>
          ))}
        </ul>
      </div>

      <form onSubmit={submit} className="card space-y-3 p-6">
        <h2 className="text-xl font-bold">{mode === "login" ? "Welcome back 👋" : "Create your account"}</h2>
        <div><label className="label">Username</label><input className="input" value={f.username} onChange={set("username")} autoComplete="username" required /></div>
        {mode === "register" && <div><label className="label">Email</label><input className="input" type="email" value={f.email} onChange={set("email")} required /></div>}
        <div><label className="label">Password</label><input className="input" type="password" placeholder={mode === "register" ? "At least 8 characters" : ""} value={f.password} onChange={set("password")} autoComplete={mode === "login" ? "current-password" : "new-password"} required /></div>
        {err && <p className="err">{err}</p>}
        <button className="btn w-full py-2.5" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}</button>
        {mode === "login" && import.meta.env.VITE_DEMO === "1" && (
          <button type="button" className="btn-ghost w-full" disabled={busy} onClick={() => go(() => login("asha", "demo12345"))}>✨ Try demo account</button>
        )}
        <div className="flex justify-between text-sm text-slate-500">
          {mode === "login"
            ? <><span>New? <Link className="font-medium text-indigo-600" to="/register">Sign up</Link></span><Link className="font-medium text-indigo-600" to="/forgot-password">Forgot password?</Link></>
            : <span>Have an account? <Link className="font-medium text-indigo-600" to="/login">Log in</Link></span>}
        </div>
      </form>
    </div>
  );
}
