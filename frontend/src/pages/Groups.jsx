import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, errText, money } from "../api";
import { AvatarStack, Empty, Spinner, Stat } from "../components/ui.jsx";

export default function Groups() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const { data, isLoading } = useQuery({ queryKey: ["groups"], queryFn: () => api("/groups/") });
  const { data: summary } = useQuery({ queryKey: ["summary"], queryFn: () => api("/summary/") });
  const netOf = (id) => summary?.groups.find((g) => g.group === id)?.net_paise ?? 0;
  const create = useMutation({
    mutationFn: () => api("/groups/", { method: "POST", body: { name } }),
    onSuccess: (g) => { setName(""); qc.invalidateQueries({ queryKey: ["groups"] }); nav(`/groups/${g.id}`); },
    onError: (e) => setErr(errText(e)),
  });
  const join = async (e) => {
    e.preventDefault(); setErr("");
    const c = code.trim().split("/").pop();
    try { const g = await api("/groups/join/", { method: "POST", body: { invite_code: c } }); nav(`/groups/${g.id}`); }
    catch (ex) { setErr(errText(ex)); }
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="You are owed" value={money(summary?.owed_paise ?? 0)} tone="green" />
        <Stat label="You owe" value={money(summary?.owe_paise ?? 0)} tone="red" />
        <div className="col-span-2 sm:col-span-1"><Stat label="Groups" value={data?.count ?? 0} /></div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <form className="card flex gap-2" onSubmit={(e) => { e.preventDefault(); setErr(""); create.mutate(); }}>
          <input className="input" placeholder="✨ New group (e.g. Goa trip)" value={name} onChange={(e) => setName(e.target.value)} required />
          <button className="btn" disabled={create.isPending}>Create</button>
        </form>
        <form className="card flex gap-2" onSubmit={join}>
          <input className="input" placeholder="🔗 Paste invite link or code" value={code} onChange={(e) => setCode(e.target.value)} required />
          <button className="btn-ghost">Join</button>
        </form>
      </div>
      {err && <p className="err">{err}</p>}

      {isLoading && <Spinner />}
      <ul className="grid gap-3 sm:grid-cols-2">
        {data?.results.map((g) => {
          const net = netOf(g.id);
          return (
            <li key={g.id}>
              <Link to={`/groups/${g.id}`} className="card block transition hover:-translate-y-0.5 hover:shadow-xl">
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div className="font-bold">{g.name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${net > 0 ? "bg-emerald-100 text-emerald-700" : net < 0 ? "bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-500"}`}>
                    {net > 0 ? `+${money(net)}` : net < 0 ? `-${money(-net)}` : "settled"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <AvatarStack users={g.members} />
                  <span className="text-xs text-slate-400">{g.members.length} member{g.members.length > 1 ? "s" : ""}</span>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
      {data?.results.length === 0 && <Empty emoji="🏝️">No groups yet. Create one above, or paste a friend's invite link.</Empty>}
    </div>
  );
}
