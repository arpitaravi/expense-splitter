import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errText, money } from "../../api";
import ExpenseForm from "../ExpenseForm.jsx";
import { CategoryBadge, Empty, Spinner } from "../ui.jsx";
import { invalidateGroup } from "./shared.js";

export default function Recurring({ group }) {
  const qc = useQueryClient();
  const gid = String(group.id);
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState(null);
  const { data } = useQuery({ queryKey: ["recurring", gid], queryFn: () => api(`/groups/${gid}/recurring/`) });
  const act = useMutation({
    mutationFn: ({ id, method, path = "", body }) => api(`/groups/${gid}/recurring/${id}/${path}`, { method, body }),
    onSuccess: (_d, v) => { if (v.path === "run/") setMsg({ ok: "Expense created for today ✓" }); invalidateGroup(qc, gid); },
    onError: (e) => setMsg({ err: errText(e) }),
  });
  if (adding) return <ExpenseForm group={group} recurring onDone={() => { setAdding(false); invalidateGroup(qc, gid); }} onCancel={() => setAdding(false)} />;
  if (!data) return <Spinner />;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-slate-500">Bills that repeat every month (rent, wifi…) are added automatically.</p>
        <button className="btn shrink-0" onClick={() => setAdding(true)}>🔁 New</button>
      </div>
      {msg?.ok && <p className="ok">{msg.ok}</p>}
      {msg?.err && <p className="err">{msg.err}</p>}
      {data.length === 0 && <Empty emoji="🔁">No recurring expenses yet.</Empty>}
      {data.map((r) => (
        <div key={r.id} className={`card flex flex-wrap items-center gap-3 ${r.active ? "" : "opacity-60"}`}>
          <div className="min-w-0 grow">
            <div className="font-semibold">{r.description}</div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <CategoryBadge category={r.category} />
              <span>{r.payer_name} pays · every month on day {r.day_of_month} · {r.split_type}{r.active ? "" : " · paused"}</span>
            </div>
          </div>
          <div className="text-lg font-extrabold">{money(r.amount_paise)}</div>
          <div className="flex w-full justify-end gap-2 sm:w-auto">
            <button className="btn-ghost" onClick={() => act.mutate({ id: r.id, method: "POST", path: "run/" })}>Add now</button>
            <button className="btn-ghost" onClick={() => act.mutate({ id: r.id, method: "PATCH", body: { active: !r.active } })}>{r.active ? "Pause" : "Resume"}</button>
            <button className="btn-danger" onClick={() => confirm("Delete this recurring expense?") && act.mutate({ id: r.id, method: "DELETE" })}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}
