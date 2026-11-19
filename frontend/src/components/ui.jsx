const AVATAR = ["bg-rose-500", "bg-amber-500", "bg-emerald-500", "bg-sky-500", "bg-violet-500", "bg-pink-500", "bg-teal-500", "bg-orange-500"];

export function Avatar({ user, size = "h-8 w-8 text-xs", ring = false }) {
  const name = user?.username || "?";
  return (
    <span title={name}
      className={`inline-flex ${size} shrink-0 items-center justify-center rounded-full font-bold text-white ${AVATAR[(user?.id ?? 0) % AVATAR.length]} ${ring ? "ring-2 ring-white" : ""}`}>
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

export function AvatarStack({ users, max = 4 }) {
  return (
    <div className="flex -space-x-2">
      {users.slice(0, max).map((u) => <Avatar key={u.id} user={u} ring />)}
      {users.length > max && (
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600 ring-2 ring-white">
          +{users.length - max}
        </span>
      )}
    </div>
  );
}

const CATS = {
  general: ["🧾", "bg-slate-100 text-slate-700"],
  food: ["🍔", "bg-orange-100 text-orange-700"],
  travel: ["✈️", "bg-sky-100 text-sky-700"],
  rent: ["🏠", "bg-violet-100 text-violet-700"],
  utilities: ["💡", "bg-amber-100 text-amber-700"],
  fun: ["🎉", "bg-pink-100 text-pink-700"],
};
export const CATEGORIES = Object.keys(CATS);
export const catEmoji = (c) => (CATS[c] || CATS.general)[0];

export function CategoryBadge({ category }) {
  const [emoji, cls] = CATS[category] || CATS.general;
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{emoji} {category}</span>;
}

export function Spinner({ text = "Loading…" }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-600" />
      {text}
    </div>
  );
}

export function Empty({ emoji = "🌱", children }) {
  return (
    <div className="card py-10 text-center text-slate-500">
      <div className="mb-1 text-3xl">{emoji}</div>
      {children}
    </div>
  );
}

export function Stat({ label, value, tone = "indigo" }) {
  const tones = {
    indigo: "from-indigo-500 to-violet-500",
    green: "from-emerald-500 to-teal-500",
    red: "from-rose-500 to-orange-500",
  };
  return (
    <div className={`rounded-2xl bg-gradient-to-br ${tones[tone]} p-4 text-white shadow-lg`}>
      <div className="text-xs font-medium uppercase tracking-wide text-white/80">{label}</div>
      <div className="mt-1 text-2xl font-extrabold">{value}</div>
    </div>
  );
}
