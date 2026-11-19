import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, errText } from "../api";
import { AvatarStack, Spinner } from "../components/ui.jsx";
import Activity from "../components/group/Activity.jsx";
import Balances from "../components/group/Balances.jsx";
import Expenses from "../components/group/Expenses.jsx";
import Insights from "../components/group/Insights.jsx";
import Members from "../components/group/Members.jsx";
import Recurring from "../components/group/Recurring.jsx";
import Settle from "../components/group/Settle.jsx";

const TABS = [
  ["Expenses", "🧾", Expenses], ["Balances", "⚖️", Balances], ["Settle up", "🤝", Settle],
  ["Recurring", "🔁", Recurring], ["Insights", "📊", Insights], ["Members", "👥", Members], ["Activity", "🕘", Activity],
];

export default function GroupDetail() {
  const { id } = useParams();
  const [tab, setTab] = useState("Expenses");
  const { data: group, error } = useQuery({ queryKey: ["group", id], queryFn: () => api(`/groups/${id}/`) });
  if (error) return <div className="card mx-auto max-w-sm space-y-3 text-center"><p className="err">{errText(error)}</p><Link className="btn" to="/">Back to groups</Link></div>;
  if (!group) return <Spinner />;
  const Active = TABS.find((t) => t[0] === tab)[2];

  return (
    <div className="space-y-4">
      <div className="card flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/" className="text-xs font-medium text-indigo-600">← All groups</Link>
          <h1 className="text-2xl font-extrabold">{group.name}</h1>
        </div>
        <AvatarStack users={group.members} max={6} />
      </div>
      <nav className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1">
        {TABS.map(([name, emoji]) => (
          <button key={name} onClick={() => setTab(name)} className={`tab ${tab === name ? "tab-active" : ""}`}>{emoji} {name}</button>
        ))}
      </nav>
      <Active group={group} />
    </div>
  );
}
