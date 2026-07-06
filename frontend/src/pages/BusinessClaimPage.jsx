import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";

export default function BusinessClaimPage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    api
      .post("/business/claim", { token })
      .then(() => {
        if (mounted) {
          navigate("/business/dashboard", { replace: true });
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err?.response?.data?.detail || "This invite link is not valid anymore.");
        }
      });
    return () => {
      mounted = false;
    };
  }, [navigate, token]);

  return (
    <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6" data-testid="business-claim-page">
      <div className="w-full max-w-md border border-white/10 bg-[#121218] p-8">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
        <h1 className="mt-4 font-flyer uppercase text-4xl leading-[0.92]">Create Account</h1>
        {error ? (
          <p className="mt-4 text-sm text-[#FF8A8A]" data-testid="business-claim-error">
            {error}
          </p>
        ) : (
          <p className="mt-4 text-sm text-white/65" data-testid="business-claim-loading">
            Verifying your access link…
          </p>
        )}
      </div>
    </div>
  );
}
