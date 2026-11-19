import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, currentUserId, money } from "../../api";
import { Avatar, Empty, Spinner } from "../ui.jsx";
import { invalidateGroup } from "./shared.js";

export default function Balances({ group }) {
  const gid = String(group.id);
  const qc = useQueryClient();
  const me = currentUserId();
  const byId = Object.fromEntries(group.members.map((m) => [m.id, m]));
  const { data } = useQuery({ queryKey: ["balances", gid], queryFn: () => api(`/groups/${gid}/balances/`) });
  const pay = useMutation({
    mutationFn: (p) => api(`/groups/${gid}/settlements/`, { method: "POST", body: { to_user: p.to_user, amount_paise: p.amount_paise } }),
    onSuccess: () => invalidateGroup(qc, gid),
  });
  if (!data) return <Spinner />;

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="card space-y-2">
        <h2 className="font-bold">Net balances</h2>
        {data.balances.map((b) => (
          <div key={b.user} className="flex items-center gap-3 rounded-xl bg-white/60 px-3 py-2">
            <Avatar user={byId[b.user] || { id: b.user, username: b.username }} />
            <span className="grow text-sm font-medium">{b.username}{b.user === me && <span className="text-slate-400"> (you)</span>}</span>
            <span className={`text-sm font-bold ${b.net_paise > 0 ? "text-emerald-600" : b.net_paise < 0 ? "text-rose-600" : "text-slate-400"}`}>
              {b.net_paise > 0 ? `gets ${money(b.net_paise)}` : b.net_paise < 0 ? `owes ${money(-b.net_paise)}` : "settled"}
            </span>
          </div>
        ))}
      </div>
      <div className="card space-y-2">
        <h2 className="font-bold">Fewest payments to settle ✨</h2>
        {data.suggested_payments.length === 0 && <Empty emoji="🎉">All settled up!</Empty>}
        {data.suggested_payments.map((p, i) => (
          <div key={i} className="flex items-center gap-2 rounded-xl bg-white/60 px-3 py-2 text-sm">
            <Avatar user={byId[p.from_user] || { id: p.from_user, username: p.from_name }} />
            <span className="grow"><b>{p.from_name}</b> pays <b>{p.to_name}</b><br /><span className="text-base font-extrabold text-indigo-700">{money(p.amount_paise)}</span></span>
            {p.from_user === me && <button className="btn" disabled={pay.isPending} onClick={() => pay.mutate(p)}>I paid</button>}
          </div>
        ))}
        {pay.isSuccess && <p className="ok text-xs">Recorded! It counts once the receiver confirms it in “Settle up”.</p>}
        {pay.isError && <p className="err text-xs">{pay.error.message}</p>}
      </div>
    </div>
  );
}
