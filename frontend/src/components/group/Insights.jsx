import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, money } from "../../api";
import { Empty, Spinner, Stat } from "../ui.jsx";

const COLORS = ["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#0ea5e9", "#8b5cf6", "#f43f5e"];

export default function Insights({ group }) {
  const gid = String(group.id);
  const { data } = useQuery({ queryKey: ["insights", gid], queryFn: () => api(`/groups/${gid}/insights/`) });
  if (!data) return <Spinner />;
  if (data.by_category.length === 0) return <Empty emoji="📊">Add some expenses to see insights.</Empty>;
  const total = data.by_category.reduce((s, r) => s + r.total_paise, 0);
  const r = (rows, key) => rows.map((x) => ({ ...x, name: x[key], rupees: x.total_paise / 100 }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Total spent" value={money(total)} />
        <Stat label="Per person (avg)" value={money(Math.round(total / group.members.length))} tone="green" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="card">
          <h2 className="mb-2 font-bold">By category</h2>
          <div className="h-60">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={r(data.by_category, "category")} dataKey="rupees" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={3}>
                  {data.by_category.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => money(v * 100)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            {data.by_category.map((c, i) => <span key={c.category} className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />{c.category}</span>)}
          </div>
        </div>
        {[["By month", data.by_month, "month"], ["Paid by member", data.by_member, "username"]].map(([title, rows, key]) => (
          <div key={title} className="card">
            <h2 className="mb-2 font-bold">{title}</h2>
            <div className="h-60">
              <ResponsiveContainer>
                <BarChart data={r(rows, key)}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip formatter={(v) => money(v * 100)} />
                  <Bar dataKey="rupees" radius={[8, 8, 0, 0]}>
                    {rows.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
