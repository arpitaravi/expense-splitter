import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, currentUserId, errText, money, toPaise } from "../../api";
import { Empty, Spinner } from "../ui.jsx";
import { invalidateGroup } from "./shared.js";

const BADGE = { pending: "bg-amber-100 text-amber-700", accepted: "bg-emerald-100 text-emerald-700", rejected: "bg-rose-100 text-rose-700" };

export default function Settle({ group }) {
  const qc = useQueryClient();
  const gid = String(group.id);
  const me = currentUserId();
  const [to, setTo] = useState("");
  const [amt, setAmt] = useState("");
  const [err, setErr] = useState("");
  const { data } = useQuery({ queryKey: ["settlements", gid], queryFn: () => api(`/groups/${gid}/settlements/`) });
  const create = useMutation({
    mutationFn: () => api(`/groups/${gid}/settlements/`, { method: "POST", body: { to_user: Number(to), amount_paise: toPaise(amt) } }),
    onSuccess: () => { setAmt(""); setErr(""); invalidateGroup(qc, gid); },
    onError: (e) => setErr(errText(e)),
  });
  const respond = useMutation({
    mutationFn: ({ id, action }) => api(`/groups/${gid}/settlements/${id}/respond/`, { method: "POST", body: { action } }),
    onSuccess: () => invalidateGroup(qc, gid),
  });
  if (!data) return <Spinner />;

  return (
    <div className="space-y-4">
      <form className="card grid gap-3 sm:grid-cols-[1fr_9rem_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <div><label className="label">I paid</label>
          <select className="input" value={to} onChange={(e) => setTo(e.target.value)} required>
            <option value="">Select person</option>
            {group.members.filter((m) => m.id !== me).map((m) => <option key={m.id} value={m.id}>{m.username}</option>)}
          </select></div>
        <div><label className="label">Amount (₹)</label><input className="input" type="number" min="0.01" step="0.01" value={amt} onChange={(e) => setAmt(e.target.value)} required /></div>
        <button className="btn" disabled={create.isPending}>Record payment</button>
        {err && <p className="err sm:col-span-3">{err}</p>}
      </form>
      {data.results.length === 0 && <Empty emoji="🤝">No payments recorded yet.</Empty>}
      {data.results.map((s) => (
        <div key={s.id} className="card flex flex-wrap items-center justify-between gap-2 text-sm">
          <span><b>{s.from_name}</b> paid <b>{s.to_name}</b> <b className="text-indigo-700">{money(s.amount_paise)}</b></span>
          <span className="flex items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${BADGE[s.status]}`}>{s.status}</span>
            {s.status === "pending" && s.to_user === me && (
              <>
                <button className="btn" onClick={() => respond.mutate({ id: s.id, action: "accept" })}>Confirm</button>
                <button className="btn-danger" onClick={() => respond.mutate({ id: s.id, action: "reject" })}>Reject</button>
              </>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
