import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errText } from "../api";
import { Avatar, Spinner } from "../components/ui.jsx";

export default function Profile() {
  const qc = useQueryClient();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api("/auth/me/") });
  const [email, setEmail] = useState("");
  const [emailMsg, setEmailMsg] = useState(null);
  const [pw, setPw] = useState({ old_password: "", new_password: "" });
  const [pwMsg, setPwMsg] = useState(null);
  useEffect(() => { if (me) setEmail(me.email); }, [me]);
  if (!me) return <Spinner />;

  async function saveEmail(e) {
    e.preventDefault();
    try { await api("/auth/me/", { method: "PATCH", body: { email } }); qc.invalidateQueries({ queryKey: ["me"] }); setEmailMsg({ ok: "Email updated ✓" }); }
    catch (ex) { setEmailMsg({ err: errText(ex) }); }
  }
  async function savePw(e) {
    e.preventDefault();
    try { const r = await api("/auth/change-password/", { method: "POST", body: pw }); setPw({ old_password: "", new_password: "" }); setPwMsg({ ok: r.detail }); }
    catch (ex) { setPwMsg({ err: errText(ex) }); }
  }
  const Msg = ({ m }) => (m?.ok ? <p className="ok">{m.ok}</p> : m?.err ? <p className="err">{m.err}</p> : null);

  return (
    <div className="mx-auto max-w-md space-y-4">
      <div className="card flex items-center gap-4">
        <Avatar user={me} size="h-14 w-14 text-xl" />
        <div><div className="text-lg font-bold">{me.username}</div><div className="text-sm text-slate-500">{me.email}</div></div>
      </div>
      <form onSubmit={saveEmail} className="card space-y-3">
        <h2 className="font-semibold">Email</h2>
        <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <Msg m={emailMsg} />
        <button className="btn">Save email</button>
      </form>
      <form onSubmit={savePw} className="card space-y-3">
        <h2 className="font-semibold">Change password</h2>
        <input className="input" type="password" placeholder="Current password" value={pw.old_password} onChange={(e) => setPw({ ...pw, old_password: e.target.value })} autoComplete="current-password" required />
        <input className="input" type="password" placeholder="New password (min 8)" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} autoComplete="new-password" required />
        <Msg m={pwMsg} />
        <button className="btn">Update password</button>
      </form>
    </div>
  );
}
