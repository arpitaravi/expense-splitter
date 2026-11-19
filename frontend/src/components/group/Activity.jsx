import { useInfiniteQuery } from "@tanstack/react-query";
import { api } from "../../api";
import { Empty, Spinner } from "../ui.jsx";

const LABEL = {
  "group.created": "🏁 created the group", "member.joined": "👋 joined the group", "member.left": "🚪 left the group",
  "member.removed": "🚫 removed a member", "member.invited": "✉️ sent invites", "expense.created": "➕ added an expense",
  "expense.updated": "✏️ edited an expense", "expense.deleted": "🗑️ deleted an expense", "expense.receipt_added": "📎 attached a receipt",
  "settlement.created": "💸 recorded a payment", "settlement.accepted": "✅ confirmed a payment", "settlement.rejected": "❌ rejected a payment",
  "recurring.created": "🔁 set up a recurring expense",
};

export default function Activity({ group }) {
  const gid = String(group.id);
  const q = useInfiniteQuery({
    queryKey: ["activity", gid],
    queryFn: ({ pageParam }) => api(`/groups/${gid}/activity/?page=${pageParam}`),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
  });
  const items = q.data?.pages.flatMap((p) => p.results) ?? [];
  if (q.isLoading) return <Spinner />;
  if (!items.length) return <Empty>Nothing yet.</Empty>;
  return (
    <div className="space-y-2">
      {items.map((a) => (
        <div key={a.id} className="card flex items-center justify-between gap-2 py-3 text-sm">
          <span><b>{a.actor_name || "Someone"}</b> {LABEL[a.action] || a.action}{a.payload?.description ? ` — ${a.payload.description}` : ""}</span>
          <span className="shrink-0 text-xs text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
        </div>
      ))}
      {q.hasNextPage && <button className="btn-ghost mx-auto flex" onClick={() => q.fetchNextPage()}>Load more</button>}
    </div>
  );
}
