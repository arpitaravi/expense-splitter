import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, currentUserId, errText } from "../../api";
import { Avatar } from "../ui.jsx";
import { invalidateGroup } from "./shared.js";

export default function Members({ group }) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const me = currentUserId();
  const isAdmin = group.created_by === me;
  const link = `${window.location.origin}/join/${group.invite_code}`;
  const [emails, setEmails] = useState("");
  const [msg, setMsg] = useState(null);
  const [copied, setCopied] = useState(false);

  async function invite(e) {
    e.preventDefault(); setMsg(null);
    try {
      const r = await api(`/groups/${group.id}/invite/`, { method: "POST", body: { emails } });
      setMsg({ ok: `Sent ${r.sent} invite${r.sent > 1 ? "s" : ""}.${r.invalid.length ? ` Skipped invalid: ${r.invalid.join(", ")}` : ""}` });
      setEmails("");
    } catch (ex) { setMsg({ err: errText(ex) }); }
  }
  async function remove(m) {
    if (!confirm(`Remove ${m.username} from this group?`)) return;
    try { await api(`/groups/${group.id}/members/${m.id}/`, { method: "DELETE" }); invalidateGroup(qc, group.id); setMsg(null); }
    catch (ex) { setMsg({ err: errText(ex) }); }
  }
  async function leave() {
    if (!confirm("Leave this group?")) return;
    try { await api(`/groups/${group.id}/leave/`, { method: "POST" }); invalidateGroup(qc, group.id); nav("/"); }
    catch (ex) { setMsg({ err: errText(ex) }); }
  }
  const copy = async () => { try { await navigator.clipboard.writeText(link); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* ignore */ } };

  return (
    <div className="space-y-4">
      <div className="card space-y-3">
        <h2 className="font-bold">Invite friends</h2>
        <div className="flex flex-wrap gap-2">
          <input readOnly className="input min-w-0 grow" value={link} onFocus={(e) => e.target.select()} />
          <button className="btn-ghost" onClick={copy}>{copied ? "Copied ✓" : "Copy link"}</button>
          <a className="btn" target="_blank" rel="noreferrer" href={`https://wa.me/?text=${encodeURIComponent(`Join "${group.name}" on Splitter: ${link}`)}`}>WhatsApp</a>
        </div>
        <form onSubmit={invite} className="flex flex-wrap gap-2">
          <input className="input min-w-0 grow" placeholder="Or email them: a@x.com, b@y.com" value={emails} onChange={(e) => setEmails(e.target.value)} required />
          <button className="btn">Send invites ✉️</button>
        </form>
        {msg?.ok && <p className="ok">{msg.ok}</p>}
        {msg?.err && <p className="err">{msg.err}</p>}
      </div>

      <div className="card space-y-2">
        <h2 className="font-bold">Members ({group.members.length})</h2>
        {group.members.map((m) => (
          <div key={m.id} className="flex items-center gap-3 rounded-xl bg-white/60 px-3 py-2">
            <Avatar user={m} size="h-9 w-9 text-sm" />
            <span className="grow font-medium">{m.username}{m.id === me && <span className="text-slate-400"> (you)</span>}</span>
            {m.id === group.created_by && <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700">Admin</span>}
            {isAdmin && m.id !== me && <button className="btn-danger" onClick={() => remove(m)}>Remove</button>}
          </div>
        ))}
        <p className="text-xs text-slate-500">Members can leave or be removed only after their balance is settled.</p>
        <button className="btn-danger" onClick={leave}>🚪 Leave group</button>
      </div>
    </div>
  );
}
