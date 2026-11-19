import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, errText } from "../api";
import { Spinner } from "../components/ui.jsx";

export default function Join() {
  const { code } = useParams();
  const nav = useNavigate();
  const [err, setErr] = useState("");
  useEffect(() => {
    api("/groups/join/", { method: "POST", body: { invite_code: code } })
      .then((g) => nav(`/groups/${g.id}`, { replace: true }))
      .catch((e) => setErr(errText(e)));
  }, [code, nav]);
  if (err) return <div className="card mx-auto max-w-sm space-y-3 text-center"><p className="err">{err}</p><Link className="btn" to="/">Go home</Link></div>;
  return <Spinner text="Joining group…" />;
}
