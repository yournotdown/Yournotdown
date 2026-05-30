import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export default function AuthCallback() {
  const navigate = useNavigate();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) {
      navigate("/admin/login");
      return;
    }
    const session_id = decodeURIComponent(m[1]);

    api
      .post("/auth/session", { session_id })
      .then((r) => {
        navigate("/admin", { state: { user: r.data.user }, replace: true });
      })
      .catch(() => {
        navigate("/admin/login", { replace: true });
      });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center" data-testid="auth-callback-page">
      <div className="text-[#A1A1AA]">Signing you in…</div>
    </div>
  );
}
