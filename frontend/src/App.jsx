import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, tokens } from "./api";
import { Avatar } from "./components/ui.jsx";
import Auth from "./pages/Auth.jsx";
import Groups from "./pages/Groups.jsx";
import GroupDetail from "./pages/GroupDetail.jsx";
import Join from "./pages/Join.jsx";
import Profile from "./pages/Profile.jsx";
import { ForgotPassword, ResetPassword } from "./pages/Reset.jsx";

function Protected({ children }) {
  return tokens.get().access ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const nav = useNavigate();
  useLocation(); // re-render on navigation so the header reflects login state
  const loggedIn = !!tokens.get().access;
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api("/auth/me/"), enabled: loggedIn });

  return (
    <div className="mx-auto max-w-4xl px-4 pb-16 pt-4">
      <header className="mb-6 flex items-center justify-between rounded-2xl bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 px-4 py-3 shadow-lg shadow-indigo-300/50">
        <Link to="/" className="text-xl font-extrabold tracking-tight text-white">💸 Splitter</Link>
        {loggedIn && (
          <nav className="flex items-center gap-2 text-sm">
            <NavLink to="/" end className={({ isActive }) => `rounded-lg px-3 py-1.5 font-medium text-white ${isActive ? "bg-white/25" : "hover:bg-white/15"}`}>Groups</NavLink>
            <NavLink to="/profile" className="flex items-center gap-2 rounded-lg px-2 py-1 text-white hover:bg-white/15">
              <Avatar user={me} size="h-7 w-7 text-xs" ring />
              <span className="hidden font-medium sm:inline">{me?.username}</span>
            </NavLink>
            <button className="rounded-lg bg-white/20 px-3 py-1.5 font-medium text-white hover:bg-white/30"
              onClick={() => { tokens.clear(); nav("/login"); }}>Log out</button>
          </nav>
        )}
      </header>
      <Routes>
        <Route path="/login" element={<Auth mode="login" />} />
        <Route path="/register" element={<Auth mode="register" />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />
        <Route path="/" element={<Protected><Groups /></Protected>} />
        <Route path="/profile" element={<Protected><Profile /></Protected>} />
        <Route path="/groups/:id" element={<Protected><GroupDetail /></Protected>} />
        <Route path="/join/:code" element={<Protected><Join /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
