import { useEffect, useState } from "react";
import { api } from "../lib/api";

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
      .catch((err) => setError(err?.response?.data?.detail || "Business access is unavailable."));
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center px-6" data-testid="business-dashboard-error">
        <div className="w-full max-w-md border border-white/10 bg-[#121218] p-8">
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
          <h1 className="mt-4 font-flyer uppercase text-4xl leading-[0.92]">Business Portal</h1>
          <p className="mt-4 text-sm text-[#FF8A8A]">{error}</p>
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
