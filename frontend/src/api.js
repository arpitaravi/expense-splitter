const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// Money is integer paise on the wire; convert only for display / input.
export const money = (paise) =>
  "₹" + (paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const toPaise = (rupees) => Math.round(parseFloat(rupees) * 100);

export const tokens = {
  get: () => ({ access: localStorage.getItem("access"), refresh: localStorage.getItem("refresh") }),
  set: ({ access, refresh }) => {
    if (access) localStorage.setItem("access", access);
    if (refresh) localStorage.setItem("refresh", refresh);
  },
  clear: () => { localStorage.removeItem("access"); localStorage.removeItem("refresh"); },
};

async function refreshAccess() {
  const { refresh } = tokens.get();
  if (!refresh) return false;
  const r = await fetch(`${BASE}/auth/token/refresh/`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh }),
  });
  if (!r.ok) { tokens.clear(); return false; }
  tokens.set(await r.json());
  return true;
}

export async function api(path, { method = "GET", body, form, retry = true } = {}) {
  const headers = {};
  const { access } = tokens.get();
  if (access) headers.Authorization = `Bearer ${access}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}${path}`, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) });
  if (res.status === 401 && retry && (await refreshAccess())) return api(path, { method, body, form, retry: false });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data));
    err.status = res.status; err.data = data;
    throw err;
  }
  return data;
}

export async function login(username, password) {
  const data = await api("/auth/token/", { method: "POST", body: { username, password } });
  tokens.set(data);
}
export async function register(username, email, password) {
  await api("/auth/register/", { method: "POST", body: { username, email, password } });
  await login(username, password);
}

export function currentUserId() {
  try {
    const payload = tokens.get().access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload)).user_id;
  } catch { return null; }
}

// Turn a DRF error payload into a readable one-liner
export function errText(e) {
  const d = e?.data;
  if (!d || typeof d !== "object") return e?.message || "Something went wrong";
  if (typeof d.detail === "string") return d.detail;
  return Object.entries(d)
    .map(([k, v]) => `${k === "non_field_errors" ? "" : k + ": "}${[].concat(v).map(String).join(" ")}`)
    .join(" · ");
}
