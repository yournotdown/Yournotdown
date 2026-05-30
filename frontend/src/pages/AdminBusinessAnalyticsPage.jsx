import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft, Eye, Globe, Phone, Navigation, Pencil, Flame,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { api, resolveImageUrl } from "../lib/api";

const METRICS = [
  { key: "business_appearance", label: "Appearances", icon: Eye, color: "#FFD166" },
  { key: "website_click", label: "Website clicks", icon: Globe, color: "#7C3AED" },
  { key: "phone_click", label: "Phone calls", icon: Phone, color: "#22D3EE" },
  { key: "directions_click", label: "Directions", icon: Navigation, color: "#A78BFA" },
];

export default function AdminBusinessAnalyticsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setData(null);
    api
      .get(`/admin/analytics/business/${id}`, { params: { days } })
      .then((r) => setData(r.data))
      .catch((e) => {
        if (e?.response?.status === 401 || e?.response?.status === 403) {
          navigate("/admin/login");
          return;
        }
        setError(e?.response?.data?.detail || "Failed to load analytics");
      });
  }, [id, days, navigate]);

  if (error) {
    return (
      <div className="min-h-screen bg-[#050505] text-white px-6 py-10" data-testid="business-analytics-error">
        <div className="max-w-3xl mx-auto text-[#A1A1AA]">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#050505] text-white px-6 py-10" data-testid="business-analytics-loading">
        <div className="max-w-3xl mx-auto text-[#A1A1AA]">Loading…</div>
      </div>
    );
  }

  const b = data.business;
  const totals = data.totals;
  const ctr =
    totals.business_appearance > 0
      ? (
          ((totals.website_click + totals.phone_click + totals.directions_click) /
            totals.business_appearance) *
          100
        ).toFixed(1)
      : "0.0";

  return (
    <div className="min-h-screen bg-[#050505] text-white" data-testid="business-analytics-page">
      <div className="border-b border-white/10 px-6 py-4">
        <button
          onClick={() => navigate("/admin")}
          className="flex items-center gap-2 text-white/60 hover:text-white text-sm transition-colors"
          data-testid="business-analytics-back"
        >
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </button>
      </div>

      <div className="px-6 py-10 max-w-6xl mx-auto">
        {/* Header card */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[#121218] border border-white/10 rounded-3xl overflow-hidden mb-10"
        >
          <div className="flex flex-col md:flex-row">
            <div className="w-full md:w-72 h-56 md:h-auto bg-[#1A1A22] relative shrink-0">
              {resolveImageUrl(b) ? (
                <img src={resolveImageUrl(b)} alt={b.name} className="w-full h-full object-cover" />
              ) : null}
              {b.featured && (
                <div className="absolute top-4 left-4 px-3 py-1.5 bg-[#7C3AED] text-white text-xs font-bold rounded-full flex items-center gap-1.5">
                  <Flame className="w-3 h-3" />
                  FEATURED
                </div>
              )}
            </div>
            <div className="flex-1 p-6 md:p-8">
              <div className="text-xs uppercase tracking-wide text-[#A1A1AA] font-bold">
                {b.category_slug} · {b.city_slug}
              </div>
              <h1
                className="font-display text-3xl md:text-4xl font-black mt-2 tracking-tight"
                data-testid="business-analytics-name"
              >
                {b.name}
              </h1>
              <p className="mt-2 text-sm text-[#A1A1AA] max-w-xl">{b.description}</p>
              <div className="mt-6 flex flex-wrap gap-2">
                <button
                  onClick={() => navigate("/admin")}
                  className="px-4 py-2 rounded-full bg-white/5 hover:bg-white/10 text-sm font-bold flex items-center gap-2 transition-colors"
                  data-testid="business-analytics-edit"
                >
                  <Pencil className="w-3.5 h-3.5" />
                  Edit business
                </button>
                <a
                  href={`/c/${b.category_slug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-full bg-white/5 hover:bg-white/10 text-sm font-bold flex items-center gap-2 transition-colors"
                  data-testid="business-analytics-view-public"
                >
                  View on site ↗
                </a>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Range selector */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
          <div>
            <h2 className="font-display text-2xl font-bold">Performance</h2>
            <p className="text-sm text-[#A1A1AA] mt-1">
              Conversion rate: <span className="text-white font-bold">{ctr}%</span> (clicks per
              impression)
            </p>
          </div>
          <div className="flex bg-[#121218] border border-white/10 rounded-full p-1">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-4 py-1.5 text-xs font-bold rounded-full transition-colors ${
                  days === d
                    ? "bg-[#7C3AED] text-white"
                    : "text-[#A1A1AA] hover:text-white"
                }`}
                data-testid={`business-analytics-range-${d}`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {/* Big number cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          {METRICS.map((m) => {
            const Icon = m.icon;
            return (
              <motion.div
                key={m.key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[#121218] border border-white/10 rounded-2xl p-5"
                data-testid={`business-metric-${m.key}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wide text-[#A1A1AA] font-bold">
                    {m.label}
                  </span>
                  <Icon className="w-4 h-4" style={{ color: m.color }} />
                </div>
                <div className="font-display text-4xl font-black mt-3">
                  {totals[m.key].toLocaleString()}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Timeline chart */}
        <div className="bg-[#121218] border border-white/10 rounded-3xl p-5 sm:p-8">
          <h3 className="font-display text-xl font-bold mb-6">Last {days} days</h3>
          <div className="w-full h-80" data-testid="business-analytics-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data.timeline}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <defs>
                  {METRICS.map((m) => (
                    <linearGradient key={m.key} id={`g-${m.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={m.color} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={m.color} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#71717A", fontSize: 11 }}
                  tickFormatter={(d) => d.slice(5)}
                  stroke="rgba(255,255,255,0.1)"
                />
                <YAxis
                  tick={{ fill: "#71717A", fontSize: 11 }}
                  stroke="rgba(255,255,255,0.1)"
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1A1A22",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                    color: "#fff",
                  }}
                  labelStyle={{ color: "#A1A1AA", fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {METRICS.map((m) => (
                  <Area
                    key={m.key}
                    type="monotone"
                    dataKey={m.key}
                    name={m.label}
                    stroke={m.color}
                    strokeWidth={2}
                    fill={`url(#g-${m.key})`}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Owner-friendly summary */}
        <div className="mt-10 bg-[#121218] border border-white/10 rounded-3xl p-6 sm:p-8">
          <h3 className="font-display text-xl font-bold mb-4">Owner-ready summary</h3>
          <p className="text-sm text-[#A1A1AA] leading-relaxed">
            Copy/paste this when talking to <span className="text-white">{b.name}</span>:
          </p>
          <pre
            className="mt-4 p-4 bg-[#0A0A0A] border border-white/5 rounded-2xl text-sm text-white whitespace-pre-wrap font-mono overflow-x-auto"
            data-testid="business-analytics-snippet"
          >
{`${b.name} — last ${days} days on You're Not Down
${totals.business_appearance.toLocaleString()} appearances in itineraries
${totals.website_click.toLocaleString()} website clicks
${totals.phone_click.toLocaleString()} phone calls
${totals.directions_click.toLocaleString()} direction requests`}
          </pre>
        </div>
      </div>
    </div>
  );
}
