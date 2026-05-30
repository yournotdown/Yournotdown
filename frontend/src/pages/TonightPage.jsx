import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft, Phone, Navigation, Globe, Dice5, RotateCw, Sparkles,
} from "lucide-react";
import { api, trackEvent, resolveImageUrl } from "../lib/api";

const VIBE_LABELS = {
  "just-vibing": { emoji: "😇", label: "Take It Easy" },
  "down": { emoji: "😏", label: "Let's See Where This Goes" },
  "very-down": { emoji: "🔥", label: "Let's Make It Count" },
  "send-it": { emoji: "🚀", label: "No Regrets" },
};

export default function TonightPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const vibe = searchParams.get("vibe") || "down";
  const vibeMeta = VIBE_LABELS[vibe] || { emoji: "✨", label: vibe };

  const [itinerary, setItinerary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [seenIds, setSeenIds] = useState([]);
  const [regenerating, setRegenerating] = useState(false);

  const generate = useCallback(
    async (excludeIds = []) => {
      setError(null);
      try {
        const r = await api.post("/itinerary/generate", {
          vibe,
          city: "nashville",
          exclude_ids: excludeIds,
        });
        setItinerary(r.data);
        // Track view (one per generation)
        trackEvent("itinerary_view", { vibe, itinerary_id: r.data.id });
        // Accumulate seen ids for variety on next regenerate
        const newIds = r.data.steps.map((s) => s.business.id);
        setSeenIds((prev) => Array.from(new Set([...prev, ...newIds])));
      } catch (e) {
        setError(e?.response?.data?.detail || "Couldn't plan tonight. Try again.");
      } finally {
        setLoading(false);
        setRegenerating(false);
      }
    },
    [vibe]
  );

  useEffect(() => {
    setLoading(true);
    setSeenIds([]);
    generate([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vibe]);

  const handleAnother = () => {
    setRegenerating(true);
    trackEvent("another_night_click", { vibe });
    generate(seenIds);
  };

  const directionsUrl = (b) => {
    const q = encodeURIComponent(b.address || b.name);
    return `https://www.google.com/maps/search/?api=1&query=${q}`;
  };

  const handleAction = (type, b, itin) => {
    trackEvent(type, { business_id: b.id, itinerary_id: itin?.id, vibe });
  };

  return (
    <div className="min-h-screen bg-[#050505] pb-24" data-testid="tonight-page">
      <div className="max-w-2xl mx-auto px-6 pt-10">
        <button
          onClick={() => navigate("/vibe")}
          className="flex items-center gap-2 text-white/60 hover:text-white text-sm mb-8 transition-colors"
          data-testid="tonight-back-button"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-2"
        >
          <div className="flex items-center gap-3 text-[#A1A1AA] text-[10px] uppercase tracking-[0.32em] font-bold">
            <Sparkles className="w-3 h-3 text-[#A855F7]" />
            Curated for tonight
          </div>
          <h1
            className="font-display font-black text-white text-5xl sm:text-6xl md:text-7xl tracking-tight leading-[0.92] mt-4"
            data-testid="tonight-headline"
          >
            TONIGHT'S<br />
            <span className="bg-gradient-to-b from-[#A855F7] to-[#7C3AED] bg-clip-text text-transparent">
              MOVE
            </span>
          </h1>
          <div className="mt-5 flex items-center gap-2 text-[#A1A1AA] text-sm">
            <span className="h-px w-8 bg-white/15" />
            <span className="text-white/70">
              {vibeMeta.emoji} {vibeMeta.label}
            </span>
          </div>
        </motion.div>

        {error ? (
          <div
            className="mt-12 p-6 rounded-3xl bg-[#121218] border border-white/10 text-[#A1A1AA]"
            data-testid="tonight-error"
          >
            {error}
            <button
              onClick={() => generate([])}
              className="mt-4 block text-[#7C3AED] font-bold hover:underline"
            >
              Try again →
            </button>
          </div>
        ) : loading && !itinerary ? (
          <div className="mt-10 space-y-6" data-testid="tonight-loading">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-64 rounded-[32px] bg-[#121218] animate-pulse" />
            ))}
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={itinerary?.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4 }}
              className="mt-10 space-y-8"
            >
              {itinerary?.steps?.length === 0 ? (
                <div className="p-6 rounded-3xl bg-[#121218] border border-white/10 text-[#A1A1AA]" data-testid="tonight-empty">
                  Catalog's a little thin. Try a different vibe or check back soon.
                </div>
              ) : (
                itinerary.steps.map((step, idx) => (
                  <StepCard
                    key={`${itinerary.id}-${step.slot}`}
                    step={step}
                    idx={idx}
                    itinerary={itinerary}
                    onAction={handleAction}
                    directionsUrl={directionsUrl}
                  />
                ))
              )}
            </motion.div>
          </AnimatePresence>
        )}

        {/* Regenerate CTA */}
        {itinerary && itinerary.steps.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="mt-12 flex flex-col items-center"
          >
            <motion.button
              onClick={handleAnother}
              disabled={regenerating}
              whileTap={{ scale: 0.97 }}
              whileHover={{ scale: 1.02 }}
              className="w-full max-w-sm py-5 px-6 btn-glass-violet glow-violet-soft disabled:opacity-60 text-white font-bold rounded-full flex items-center justify-center gap-3 transition-all"
              data-testid="tonight-another-button"
            >
              {regenerating ? (
                <RotateCw className="w-5 h-5 animate-spin" />
              ) : (
                <Dice5 className="w-5 h-5" />
              )}
              <span className="tracking-[0.18em]">GIVE ME ANOTHER NIGHT</span>
            </motion.button>
            <p className="mt-4 text-[10px] uppercase tracking-[0.32em] text-white/30">
              Every night is different
            </p>
          </motion.div>
        )}
      </div>
    </div>
  );
}

function StepCard({ step, idx, itinerary, onAction, directionsUrl }) {
  const b = step.business;
  const sponsored = b.sponsor_tier && b.sponsor_tier !== "none";

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.08, duration: 0.45 }}
      className="relative"
      data-testid={`tonight-step-${step.slot}`}
    >
      {/* Concierge step header */}
      <div className="flex items-baseline gap-4 mb-5">
        <div
          className="font-display font-black text-[#7C3AED]/80 text-5xl sm:text-6xl leading-none tabular-nums"
          aria-hidden
        >
          {String(step.number).padStart(2, "0")}
        </div>
        <div className="flex-1">
          <div className="text-[10px] uppercase tracking-[0.32em] font-bold text-[#A1A1AA]">
            Step {step.number} of 4
          </div>
          <div className="font-display font-bold text-white text-2xl sm:text-3xl flex items-center gap-2 mt-1">
            <span>{step.label}</span>
            <span aria-hidden className="text-base opacity-70">{step.emoji}</span>
          </div>
        </div>
      </div>

      {/* Business card */}
      <div
        className="bg-[#121218] rounded-[32px] overflow-hidden border border-white/10 shadow-2xl group"
        data-testid={`tonight-business-card-${b.id}`}
      >
        <div className="relative w-full h-64 sm:h-72 bg-[#1A1A22] overflow-hidden">
          {resolveImageUrl(b) && (
            <img
              src={resolveImageUrl(b)}
              alt={b.name}
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              loading="lazy"
            />
          )}
          {sponsored && (
            <div
              className="absolute top-4 left-4 px-2.5 py-1 bg-black/50 backdrop-blur border border-[#A855F7]/30 text-[#A855F7] text-[9px] uppercase tracking-[0.32em] font-bold rounded-full"
              data-testid={`tonight-sponsored-badge-${b.id}`}
            >
              Sponsored
            </div>
          )}
        </div>
        <div className="p-6 sm:p-7">
          <h3
            className="font-display text-2xl sm:text-3xl font-bold text-white tracking-tight"
            data-testid={`tonight-business-name-${b.id}`}
          >
            {b.name}
          </h3>
          <p className="mt-2 text-[#A1A1AA] text-sm leading-relaxed line-clamp-3">
            {b.description}
          </p>
          <div className="grid grid-cols-3 gap-2.5 mt-6">
            {b.phone ? (
              <a
                href={`tel:${b.phone}`}
                onClick={() => onAction("phone_click", b, itinerary)}
                className="py-3.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95"
                data-testid={`tonight-call-${b.id}`}
              >
                <Phone className="w-4 h-4" />
                <span className="hidden sm:inline">Call</span>
              </a>
            ) : <div />}
            {b.address || b.name ? (
              <a
                href={directionsUrl(b)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => onAction("directions_click", b, itinerary)}
                className="py-3.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/5 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95"
                data-testid={`tonight-directions-${b.id}`}
              >
                <Navigation className="w-4 h-4" />
                <span className="hidden sm:inline">Directions</span>
              </a>
            ) : <div />}
            {b.website ? (
              <a
                href={b.website}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => onAction("website_click", b, itinerary)}
                className="py-3.5 rounded-full btn-glass-violet text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95 glow-violet-soft"
                data-testid={`tonight-website-${b.id}`}
              >
                <Globe className="w-4 h-4" />
                <span className="hidden sm:inline">Website</span>
              </a>
            ) : <div />}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
