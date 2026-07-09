import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import PublicFooter from "../components/PublicFooter";

const loginClaimError = (err) => {
  const detail = err?.response?.data?.detail || "";
  if (detail === "Invalid or expired login link." || detail === "This login link has expired.") {
    return "This secure login link is no longer valid. Request a fresh magic link below.";
  }
  if (detail === "This login link has already been used." || detail === "This login link is no longer active.") {
    return "This secure login link can’t be used anymore. Request a fresh magic link below.";
  }
  return detail || "Business access is unavailable right now.";
};

export default function BusinessLoginPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [claiming, setClaiming] = useState(Boolean(token));

  useEffect(() => {
    let mounted = true;
    if (!token) {
      setClaiming(false);
      return () => {
        mounted = false;
      };
    }
    (async () => {
      try {
        await api.post("/business/login-claim", { token });
        await api.get("/business/me");
        if (mounted) {
          window.location.replace("/business/dashboard");
        }
      } catch (err) {
        if (mounted) {
          setError(loginClaimError(err));
          setClaiming(false);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, [token]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const response = await api.post("/business/login-request", { email });
      setSuccess(response?.data?.message || "If your email has access, we’ll send a secure login link.");
    } catch (err) {
      setError(err?.response?.data?.detail || "We couldn’t send a login link right now.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6" data-testid="business-login-page">
      <div className="w-full max-w-md border border-white/10 bg-[#121218] p-8">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
        <h1 className="mt-4 font-flyer uppercase text-4xl leading-[0.92]">Access your business dashboard</h1>
        <p className="mt-4 text-sm text-white/65">
          Enter the email tied to your active business access and we&apos;ll send a secure magic link.
        </p>
        {claiming ? (
          <p className="mt-6 text-sm text-white/65" data-testid="business-login-claiming">
            Verifying your secure login link…
          </p>
        ) : (
          <form className="mt-6" onSubmit={handleSubmit}>
            <label className="block text-[10px] uppercase tracking-[0.24em] text-white/45" htmlFor="business-login-email">
              Email
            </label>
            <input
              id="business-login-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              autoComplete="email"
              data-testid="business-login-email"
              required
            />
            <button
              type="submit"
              className="mt-4 w-full bg-[#C6FF00] px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-black disabled:opacity-60"
              disabled={submitting}
              data-testid="business-login-submit"
            >
              {submitting ? "Sending..." : "Send Magic Link"}
            </button>
          </form>
        )}
        {success ? (
          <p className="mt-4 text-sm text-[#C6FF00]" data-testid="business-login-success">
            {success}
          </p>
        ) : null}
        {error ? (
          <p className="mt-4 text-sm text-[#FF8A8A]" data-testid="business-login-error">
            {error}
          </p>
        ) : null}
        <PublicFooter className="mt-8 border-t border-white/10 pt-5" />
      </div>
    </div>
  );
}
