import { useState } from "react";
import { api, errText, toPaise } from "../api";
import { Avatar, CATEGORIES, catEmoji } from "./ui.jsx";

const HINT = {
  equal: "Everyone ticked pays the same share.",
  exact: "Type each person's amount in ₹. They must add up to the total.",
  percent: "Type each person's percentage. They must total 100.",
  shares: "Type weights, e.g. 2 nights vs 1 night = 2 and 1.",
};

/** Used for both one-off expenses and recurring templates (recurring = true). */
export default function ExpenseForm({ group, expense, recurring = false, onDone, onCancel }) {
  const editing = !!expense;
  const [f, setF] = useState({
    description: expense?.description || "",
    amount: expense ? (expense.amount_paise / 100).toString() : "",
    category: expense?.category || (recurring ? "rent" : "general"),
    date: expense?.date || new Date().toISOString().slice(0, 10),
    day_of_month: 1,
    payer: expense?.payer || group.members[0].id,
    split_type: expense?.split_type || "equal",
  });
  const [parts, setParts] = useState(() =>
    Object.fromEntries(group.members.map((m) => {
      const s = expense?.splits.find((x) => x.user === m.id);
      return [m.id, { included: editing ? !!s : true, value: "" }];
    })));
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const setPart = (id, patch) => setParts({ ...parts, [id]: { ...parts[id], ...patch } });

  async function submit(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    const participants = group.members.filter((m) => parts[m.id].included).map((m) => {
      const raw = parts[m.id].value;
      let value = null;
      if (f.split_type === "exact") value = toPaise(raw || "0");
      else if (f.split_type !== "equal") value = raw === "" ? null : Number(raw);
      return { user: m.id, value };
    });
    const body = {
      payer: Number(f.payer), amount_paise: toPaise(f.amount), description: f.description,
      category: f.category, split_type: f.split_type, participants,
      ...(recurring ? { day_of_month: Number(f.day_of_month) } : { date: f.date }),
      ...(editing ? { version: expense.version } : {}),
    };
    try {
      if (recurring) await api(`/groups/${group.id}/recurring/`, { method: "POST", body });
      else if (editing) await api(`/groups/${group.id}/expenses/${expense.id}/`, { method: "PUT", body });
      else await api(`/groups/${group.id}/expenses/`, { method: "POST", body });
      onDone();
    } catch (ex) { setErr(errText(ex)); } finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className="card space-y-4">
      <h2 className="text-lg font-bold">{recurring ? "🔁 New recurring expense" : editing ? "Edit expense" : "➕ Add expense"}</h2>
      <div><label className="label">What was it for?</label>
        <input className="input" placeholder={recurring ? "e.g. Monthly rent" : "e.g. Dinner at the beach shack"} value={f.description} onChange={set("description")} required /></div>
      <div className="grid grid-cols-2 gap-3">
        <div><label className="label">Total (₹)</label><input className="input" type="number" min="0.01" step="0.01" value={f.amount} onChange={set("amount")} required /></div>
        {recurring
          ? <div><label className="label">Repeats on day (1–28)</label><input className="input" type="number" min="1" max="28" value={f.day_of_month} onChange={set("day_of_month")} required /></div>
          : <div><label className="label">Date</label><input className="input" type="date" value={f.date} onChange={set("date")} required /></div>}
        <div><label className="label">Category</label>
          <select className="input" value={f.category} onChange={set("category")}>{CATEGORIES.map((c) => <option key={c} value={c}>{catEmoji(c)} {c}</option>)}</select></div>
        <div><label className="label">Paid by</label>
          <select className="input" value={f.payer} onChange={set("payer")}>{group.members.map((m) => <option key={m.id} value={m.id}>{m.username}</option>)}</select></div>
      </div>
      <div>
        <label className="label">How to split</label>
        <div className="flex flex-wrap gap-2">
          {[["equal", "Equally"], ["exact", "Exact ₹"], ["percent", "Percent %"], ["shares", "Shares"]].map(([v, l]) => (
            <button type="button" key={v} onClick={() => setF({ ...f, split_type: v })}
              className={`tab ${f.split_type === v ? "tab-active" : "bg-white/70 ring-1 ring-slate-200"}`}>{l}</button>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">{HINT[f.split_type]}</p>
      </div>
      <div className="space-y-2">
        {group.members.map((m) => (
          <label key={m.id} className="flex items-center gap-3 rounded-xl bg-white/60 px-3 py-2 text-sm">
            <input type="checkbox" className="h-4 w-4 accent-indigo-600" checked={parts[m.id].included} onChange={(e) => setPart(m.id, { included: e.target.checked })} />
            <Avatar user={m} />
            <span className="grow font-medium">{m.username}</span>
            {f.split_type !== "equal" && parts[m.id].included && (
              <input className="input !w-28" type="number" step="0.01" placeholder={f.split_type === "exact" ? "₹" : f.split_type === "percent" ? "%" : "weight"}
                value={parts[m.id].value} onChange={(e) => setPart(m.id, { value: e.target.value })} />
            )}
          </label>
        ))}
      </div>
      {err && <p className="err">{err}</p>}
      <div className="flex gap-2">
        <button className="btn" disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : recurring ? "Create" : "Add expense"}</button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
