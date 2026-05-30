import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Phone, Navigation, Globe, RotateCw } from "lucide-react";
import { api, trackEvent, resolveImageUrl } from "../lib/api";

const VIBE_LABELS = {
  "just-vibing": { emoji: "😇", label: "Take It Easy" },
  down: { emoji: "😏", label: "Let's See Where This Goes" },
  "very-down": { emoji: "🔥", label: "Let's Make It Count" },
  "send-it": { emoji: "🚀", label: "No Regrets" },
};

const SLOT_TIMES = {
  dinner: "7:00 PM",
  drinks: "9:00 PM",
  entertainment: "10:30 PM",
  "late-night": "12:00 AM",
};

const SLOT_TITLES = {
  dinner: "DINNER",
  drinks: "DRINKS",
  entertainment: "LIVE MUSIC",
  "late-night": "LATE NIGHT",
};

const MARQUEE = "THE NIGHT IS ALREADY HAPPENING";

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
        trackEvent("itinerary_view", { vibe, itinerary_id: r.data.id });
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

  const handleAction = (type, b) => {
    trackEvent(type, { business_id: b.id, itinerary_id: itinerary?.id, vibe });
  };

  return (
    <div
      className="relative min-h-screen bg-black text-white overflow-hidden"
      data-testid="tonight-page"
    >
      {/* Atmospherics */}
      <div className="pointer-events-none absolute inset-0 film-grain opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_55%,_#000_100%)]" />
      <div className="pointer-events-none absolute inset-0 strobe-dim bg-black" />
      <div className="pointer-events-none absolute inset-x-0 h-px bg-white/40 scanline-anim" />

      {/* Corner marks */}
      <div className="absolute top-5 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        YND <span className="lime-dot mx-1.5">/</span> ONE NIGHT ONLY
      </div>
      <div className="absolute top-5 right-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        Vol. 003
      </div>

      <button
        onClick={() => navigate("/vibe")}
        className="absolute top-14 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/50 hover:text-[#C6FF00] transition-colors"
        data-testid="tonight-back-button"
      >
        ← Back
      </button>

      {/* HEADER POSTER */}
      <div className="relative z-10 px-6 sm:px-10 pt-28 pb-10 sm:pb-14">
        <div className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-4">
          Curated by YND <span className="lime-dot mx-1.5">·</span> {vibeMeta.emoji} {vibeMeta.label}
        </div>
        <motion.h1
          className="font-flyer text-white uppercase"
          style={{
            fontSize: "clamp(2.8rem, 11vw, 9rem)",
            transform: "rotate(-1.5deg)",
            transformOrigin: "left",
            lineHeight: "0.85",
          }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          data-testid="tonight-headline"
        >
          Tonight's<br />Move<span className="lime-dot">.</span>
        </motion.h1>
      </div>

      {/* SETLIST */}
      <div className="relative z-10 px-6 sm:px-10 pb-20 max-w-6xl">
        {error ? (
          <div className="border-t border-white/10 py-10 text-white/60" data-testid="tonight-error">
            {error}
            <button
              onClick={() => generate([])}
              className="mt-4 block font-flyer uppercase text-[#C6FF00] hover:underline text-sm tracking-[0.2em]"
            >
              Try again →
            </button>
          </div>
        ) : loading && !itinerary ? (
          <div className="space-y-0" data-testid="tonight-loading">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="border-t border-white/10 py-12">
                <div className="h-12 w-40 bg-white/5 animate-pulse" />
                <div className="mt-6 h-20 w-3/4 bg-white/5 animate-pulse" />
              </div>
            ))}
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={itinerary?.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -14 }}
              transition={{ duration: 0.4 }}
            >
              {itinerary?.steps?.length === 0 ? (
                <div
                  className="border-t border-white/10 py-10 text-white/60"
                  data-testid="tonight-empty"
                >
                  The catalog's thin. Pick a different vibe.
                </div>
              ) : (
                itinerary.steps.map((step, idx) => (
                  <SetCard
                    key={`${itinerary.id}-${step.slot}`}
                    step={step}
                    idx={idx}
                    onAction={handleAction}
                    directionsUrl={directionsUrl}
                  />
                ))
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* "Another Night" CTA — poster style */}
      {itinerary && itinerary.steps.length > 0 && (
        <motion.div
          className="relative z-10 px-6 sm:px-10 pb-32 border-t border-white/10 pt-12"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-3">
            Don't like this one<span className="lime-dot mx-1.5">?</span>
          </div>
          <motion.button
            onClick={handleAnother}
            disabled={regenerating}
            className="group font-flyer text-white hover:text-[#C6FF00] disabled:opacity-50 uppercase text-left leading-[0.88] transition-colors"
            style={{ fontSize: "clamp(2.2rem, 8vw, 6rem)" }}
            whileTap={{ scale: 0.985 }}
            data-testid="tonight-another-button"
          >
            <span className="inline-flex items-center gap-3 sm:gap-5">
              {regenerating ? (
                <RotateCw className="w-8 h-8 sm:w-12 sm:h-12 animate-spin" />
              ) : (
                <span aria-hidden className="inline-block group-hover:rotate-180 transition-transform duration-500">
                  ↺
                </span>
              )}
              Give me another night<span className="lime-dot">.</span>
            </span>
          </motion.button>
        </motion.div>
      )}

      {/* Marquee */}
      <div className="absolute bottom-0 inset-x-0 z-10 border-t border-white/10 bg-black/80 backdrop-blur-sm overflow-hidden">
        <div className="marquee-track flex whitespace-nowrap py-3 sm:py-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <span
              key={i}
              className="font-flyer text-sm sm:text-base px-6 tracking-[0.18em] text-white/70"
            >
              {MARQUEE}
              <span className="lime-dot mx-3">·</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function SetCard({ step, idx, onAction, directionsUrl }) {
  const b = step.business;
  const sponsored = b.sponsor_tier && b.sponsor_tier !== "none";
  const time = SLOT_TIMES[step.slot] || "TBD";
  const title = SLOT_TITLES[step.slot] || step.label.toUpperCase();

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="border-t border-white/10 py-10 sm:py-14"
      data-testid={`tonight-step-${step.slot}`}
    >
      <div className="grid grid-cols-12 gap-4 sm:gap-8 items-start">
        {/* TIME (poster column) */}
        <div className="col-span-12 sm:col-span-3">
          <div
            className="font-flyer text-white leading-none"
            style={{ fontSize: "clamp(2rem, 6vw, 4.5rem)" }}
          >
            {time}
          </div>
          <div className="mt-3 text-[10px] uppercase tracking-[0.3em] text-white/40">
            Set {String(idx + 1).padStart(2, "0")} <span className="text-white/20">/ 04</span>
          </div>
        </div>

        {/* BUSINESS (poster column) */}
        <div className="col-span-12 sm:col-span-9">
          <div className="text-[10px] uppercase tracking-[0.3em] mb-3 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[#C6FF00]">{title}</span>
            {sponsored && (
              <>
                <span className="text-white/30">·</span>
                <span
                  className="text-[#C6FF00]"
                  data-testid={`tonight-sponsored-badge-${b.id}`}
                >
                  Featured Tonight
                </span>
              </>
            )}
          </div>

          <h2
            className="font-flyer uppercase text-white leading-[0.85]"
            style={{ fontSize: "clamp(2rem, 7vw, 5rem)" }}
            data-testid={`tonight-business-name-${b.id}`}
          >
            {b.name}
          </h2>

          <div className="mt-6 grid grid-cols-12 gap-4 sm:gap-6">
            <div className="col-span-12 sm:col-span-5 relative aspect-[4/3] overflow-hidden border border-white/10 bg-[#0A0A0A]">
              {resolveImageUrl(b) && (
                <img
                  src={resolveImageUrl(b)}
                  alt={b.name}
                  className="w-full h-full object-cover grayscale-[15%] hover:grayscale-0 transition-all duration-700"
                  loading="lazy"
                />
              )}
            </div>
            <div className="col-span-12 sm:col-span-7 flex flex-col justify-between gap-6">
              <p className="text-white/65 text-sm leading-relaxed">{b.description}</p>
              <div className="flex flex-wrap gap-2">
                {b.phone ? (
                  <ActionBtn
                    href={`tel:${b.phone}`}
                    onClick={() => onAction("phone_click", b)}
                    testid={`tonight-call-${b.id}`}
                    icon={<Phone className="w-3.5 h-3.5" />}
                  >
                    Call
                  </ActionBtn>
                ) : null}
                {b.address || b.name ? (
                  <ActionBtn
                    href={directionsUrl(b)}
                    target="_blank"
                    onClick={() => onAction("directions_click", b)}
                    testid={`tonight-directions-${b.id}`}
                    icon={<Navigation className="w-3.5 h-3.5" />}
                  >
                    Directions
                  </ActionBtn>
                ) : null}
                {b.website ? (
                  <ActionBtn
                    href={b.website}
                    target="_blank"
                    onClick={() => onAction("website_click", b)}
                    testid={`tonight-website-${b.id}`}
                    icon={<Globe className="w-3.5 h-3.5" />}
                    primary
                  >
                    Website
                  </ActionBtn>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ActionBtn({ children, href, target, onClick, testid, icon, primary }) {
  return (
    <a
      href={href}
      target={target}
      rel={target ? "noopener noreferrer" : undefined}
      onClick={onClick}
      data-testid={testid}
      className={`inline-flex items-center gap-2 px-4 py-3 border uppercase text-[10px] tracking-[0.22em] font-bold transition-colors active:scale-95 ${
        primary
          ? "bg-[#C6FF00] text-black border-[#C6FF00] hover:bg-white hover:border-white"
          : "border-white/20 text-white hover:border-[#C6FF00] hover:text-[#C6FF00]"
      }`}
    >
      {icon}
      <span>{children}</span>
    </a>
  );
}
