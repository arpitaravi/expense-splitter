import { useState } from "react";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, money } from "../../api";
import ExpenseForm from "../ExpenseForm.jsx";
import { Avatar, CategoryBadge, Empty, Spinner } from "../ui.jsx";
import { invalidateGroup } from "./shared.js";

export default function Expenses({ group }) {
  const qc = useQueryClient();
  const gid = String(group.id);
  const [editing, setEditing] = useState(null);
  const [adding, setAdding] = useState(false);
  const [err, setErr] = useState("");
  const q = useInfiniteQuery({
    queryKey: ["expenses", gid],
    queryFn: ({ pageParam }) => api(`/groups/${gid}/expenses/?page=${pageParam}`),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
  });
  const items = q.data?.pages.flatMap((p) => p.results) ?? [];
  const byId = Object.fromEntries(group.members.map((m) => [m.id, m]));
  const del = useMutation({
    mutationFn: (e) => api(`/groups/${gid}/expenses/${e.id}/?version=${e.version}`, { method: "DELETE" }),
    onSuccess: () => invalidateGroup(qc, gid),
    onError: (e) => setErr(e.message),
  });
  async function upload(e, file) {
    const form = new FormData();
    form.append("receipt", file);
    try { await api(`/groups/${gid}/expenses/${e.id}/receipt/`, { method: "POST", form }); invalidateGroup(qc, gid); }
    catch (ex) { setErr(ex.message); }
  }

  if (adding || editing)
    return <ExpenseForm group={group} expense={editing}
      onDone={() => { setAdding(false); setEditing(null); invalidateGroup(qc, gid); }}
      onCancel={() => { setAdding(false); setEditing(null); }} />;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">{q.data?.pages[0].count ?? 0} expenses</span>
        <button className="btn" onClick={() => setAdding(true)}>➕ Add expense</button>
      </div>
      {err && <p className="err">{err}</p>}
      {q.isLoading && <Spinner />}
      {items.map((e) => (
        <div key={e.id} className="card flex flex-wrap items-center gap-3">
          <Avatar user={byId[e.payer] || { id: e.payer, username: e.payer_name }} size="h-10 w-10 text-sm" />
          <div className="min-w-0 grow">
            <div className="truncate font-semibold">{e.description}</div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <CategoryBadge category={e.category} />
              <span>{e.payer_name} paid · {e.date} · {e.split_type}</span>
              {e.receipt && <a className="font-medium text-indigo-600" href={e.receipt} target="_blank" rel="noreferrer">📎 receipt</a>}
            </div>
          </div>
          <div className="text-right"><div className="text-lg font-extrabold">{money(e.amount_paise)}</div></div>
          <div className="flex w-full justify-end gap-2 sm:w-auto">
            <label className="btn-ghost">📎
              <input type="file" className="hidden" accept="image/png,image/jpeg,application/pdf"
                onChange={(ev) => ev.target.files[0] && upload(e, ev.target.files[0])} />
            </label>
            <button className="btn-ghost" onClick={() => setEditing(e)}>Edit</button>
            <button className="btn-danger" onClick={() => confirm("Delete this expense?") && del.mutate(e)}>Delete</button>
          </div>
        </div>
      ))}
      {!q.isLoading && items.length === 0 && <Empty emoji="🧾">No expenses yet. Add the first one!</Empty>}
      {q.hasNextPage && (
        <button className="btn-ghost mx-auto flex" disabled={q.isFetchingNextPage} onClick={() => q.fetchNextPage()}>
          {q.isFetchingNextPage ? "Loading…" : "Load more"}
        </button>
      )}
    </div>
  );
}
