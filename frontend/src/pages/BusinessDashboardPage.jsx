import { useEffect, useState } from "react";
import { api } from "../lib/api";

const ownerSessionError = (err) => {
  const detail = err?.response?.data?.detail || "";
  if (detail === "Not authenticated" || detail === "Invalid session" || detail === "Session revoked" || detail === "Session expired") {
    return "Your session expired. Request a fresh secure login link.";
  }
  if (detail === "Owner access revoked") {
    return "Your business portal access is no longer active.";
  }
  return detail || "Business access is unavailable.";
};

const EMPTY_ANALYTICS = {
  appearances: 0,
  locked_in: 0,
  saved_in_final_move: 0,
  website_clicks: 0,
  directions_clicks: 0,
  ticket_clicks: 0,
  phone_clicks: 0,
  total_engagement: 0,
};

export default function BusinessDashboardPage() {
  const [owner, setOwner] = useState(null);
  const [analytics, setAnalytics] = useState(EMPTY_ANALYTICS);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/business/me").then((r) => r.data),
      api.get("/business/analytics").then((r) => r.data).catch(() => EMPTY_ANALYTICS),
    ])
      .then(([ownerData, analyticsData]) => {
        setOwner(ownerData);
        setAnalytics({ ...EMPTY_ANALYTICS, ...(analyticsData || {}) });
      })
      .catch((err) => setError(ownerSessionError(err)));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6" data-testid="business-dashboard-error">
        <div className="w-full max-w-md border border-white/10 bg-[#121218] p-8">
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
          <h1 className="mt-4 font-flyer uppercase text-4xl leading-[0.92]">Business Portal</h1>
          <p className="mt-4 text-sm text-[#FF8A8A]">{error}</p>
          <a
            href="/business/login"
            className="mt-5 inline-block text-[11px] font-black uppercase tracking-[0.22em] text-[#C6FF00]"
            data-testid="business-dashboard-login-link"
          >
            Send me a login link
          </a>
        </div>
      </div>
    );
  }

  if (!owner) {
    return (
      <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6" data-testid="business-dashboard-loading">
        <div className="w-full max-w-md border border-white/10 bg-[#121218] p-8">
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
          <h1 className="mt-4 font-flyer uppercase text-4xl leading-[0.92]">Business Portal</h1>
          <p className="mt-4 text-sm text-white/65">Loading your business dashboard…</p>
        </div>
      </div>
    );
  }

  const business = owner.business || {};
  const ownerEmail = owner.email || "";
  const supportHref = "mailto:hello@yournotdown.com";
  const cards = [
    { label: "Appearances", value: analytics.appearances },
    { label: "Locked In", value: analytics.locked_in },
    { label: "Saved in Final Move", value: analytics.saved_in_final_move },
    { label: "Website Clicks", value: analytics.website_clicks },
    { label: "Directions Clicks", value: analytics.directions_clicks },
    { label: "Buy Tickets", value: analytics.ticket_clicks },
    { label: "Phone Clicks", value: analytics.phone_clicks },
    { label: "Total Engagement", value: analytics.total_engagement },
  ];

  return (
    <div className="min-h-screen bg-[#050505] text-white px-6 py-10" data-testid="business-dashboard-page">
      <div className="max-w-5xl mx-auto">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
        <div className="mt-3 text-[10px] uppercase tracking-[0.26em] text-white/45">Business Portal</div>
        <h1 className="mt-3 font-flyer uppercase text-5xl leading-[0.9]" data-testid="business-dashboard-name">
          {business.name || "Your Venue"}
        </h1>
        <p className="mt-4 text-sm text-white/65 max-w-2xl">
          Sponsor tier: <span className="text-white">{business.sponsor_tier || "none"}</span>. Your portal includes your venue snapshot and current performance totals.
        </p>

        <div className="mt-8 border border-white/10 bg-[#121218] p-6" data-testid="business-dashboard-access">
          <div className="text-[10px] uppercase tracking-[0.24em] text-[#C6FF00]">Account Access</div>
          <h2 className="mt-3 font-flyer uppercase text-3xl leading-[0.95]">Your dashboard access is active.</h2>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-white/68">
            Your access is connected to this email. To return later, visit <span className="text-white">yournotdown.com/business/login</span> and request a secure magic link.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div className="border border-white/8 bg-black/20 p-4">
              <div className="text-[10px] uppercase tracking-[0.22em] text-white/45">Email</div>
              <div className="mt-2 text-sm text-white break-all" data-testid="business-dashboard-email">{ownerEmail || "Active access email"}</div>
            </div>
            <div className="border border-white/8 bg-black/20 p-4">
              <div className="text-[10px] uppercase tracking-[0.22em] text-white/45">Business</div>
              <div className="mt-2 text-sm text-white">{business.name || "Your Venue"}</div>
            </div>
            <div className="border border-white/8 bg-black/20 p-4">
              <div className="text-[10px] uppercase tracking-[0.22em] text-white/45">Sponsor Tier</div>
              <div className="mt-2 text-sm text-white">{business.sponsor_tier || "none"}</div>
            </div>
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <a
              href="/business/login"
              className="inline-flex items-center justify-center border border-[#C6FF00] px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-[#C6FF00]"
              data-testid="business-dashboard-return-login"
            >
              Return login page
            </a>
            <a
              href={supportHref}
              className="inline-flex items-center justify-center border border-white/14 px-4 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-white/80"
              data-testid="business-dashboard-help"
            >
              Need help?
            </a>
          </div>
        </div>

        <div className="mt-10 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {cards.map((card) => (
            <div key={card.label} className="border border-white/10 bg-[#121218] p-5">
              <div className="text-[10px] uppercase tracking-[0.22em] text-[#A1A1AA] font-bold">{card.label}</div>
              <div className="mt-3 font-display text-4xl font-black">{(card.value || 0).toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
