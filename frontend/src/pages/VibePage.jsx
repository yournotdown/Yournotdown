import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { trackEvent } from "../lib/api";

const VIBES = [
  { slug: "just-vibing", emoji: "😇", label: "Take It Easy" },
  { slug: "down", emoji: "😏", label: "Let's See Where This Goes" },
  { slug: "very-down", emoji: "🔥", label: "Let's Make It Count" },
  { slug: "send-it", emoji: "🚀", label: "No Regrets" },
];

const MARQUEE = "PICK YOUR VERSION OF THE NIGHT";

export default function VibePage() {
  const navigate = useNavigate();
  const [crashing, setCrashing] = useState(false);

  const handleSelect = (vibe) => {
    if (crashing) return;
    trackEvent("vibe_click", { vibe: vibe.slug });
    setCrashing(true);
    setTimeout(() => navigate(`/tonight?vibe=${vibe.slug}`), 420);
  };

  return (
    <div
      className="relative min-h-screen bg-black text-white overflow-hidden"
      data-testid="vibe-page"
    >
      {/* Atmospherics — match homepage exactly */}
      <div className="pointer-events-none absolute inset-0 film-grain opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_55%,_#000_100%)]" />
      <div className="pointer-events-none absolute inset-0 strobe-dim bg-black" />
      <div className="pointer-events-none absolute inset-x-0 h-px bg-white/40 scanline-anim" />

      {/* Crash flash on select */}
      <AnimatePresence>
        {crashing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 1, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.42, times: [0, 0.15, 0.55, 1] }}
            className="pointer-events-none fixed inset-0 z-50 bg-[#C6FF00]"
          />
        )}
      </AnimatePresence>

      {/* Corner marks */}
      <div className="absolute top-5 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        YND <span className="lime-dot mx-1.5">/</span> EST. 26
      </div>
      <div className="absolute top-5 right-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        Vol. 002
      </div>

      <button
        onClick={() => navigate("/")}
        className="absolute top-14 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/50 hover:text-[#C6FF00] transition-colors"
        data-testid="vibe-back-button"
      >
        ← Back
      </button>

      {/* Content */}
      <motion.div
        className="relative z-10 min-h-screen flex flex-col justify-center pt-28 pb-28 px-6 sm:px-10"
        animate={crashing ? { scale: 0.96, opacity: 0 } : { scale: 1, opacity: 1 }}
        transition={{ duration: 0.32 }}
      >
        <motion.h1
          className="font-flyer text-white uppercase"
          style={{
            fontSize: "clamp(2.2rem, 7vw, 6rem)",
            transform: "rotate(-1.5deg)",
            transformOrigin: "left",
          }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55 }}
          data-testid="vibe-headline"
        >
          How down<br />are you<span className="lime-dot">?</span>
        </motion.h1>

        <div className="mt-10 sm:mt-14 border-t border-white/10">
          {VIBES.map((v, i) => (
            <motion.button
              key={v.slug}
              onClick={() => handleSelect(v)}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08 + i * 0.06, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              className="group relative w-full flex items-center justify-between gap-4 sm:gap-6 py-6 sm:py-7 border-b border-white/10 transition-colors hover:bg-white/[0.025] focus:outline-none cursor-pointer"
              data-testid={`vibe-btn-${v.slug}`}
            >
              {/* Hover lime sweep on left */}
              <span
                aria-hidden
                className="absolute left-0 top-0 bottom-0 w-0 group-hover:w-1 bg-[#C6FF00] transition-all duration-300"
              />
              <div className="flex items-baseline gap-3 sm:gap-6 min-w-0 text-left">
                <span className="font-flyer text-white/30 text-[11px] uppercase tracking-[0.3em] tabular-nums shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span
                  className="font-flyer uppercase text-white group-hover:text-[#C6FF00] transition-colors leading-[0.88]"
                  style={{ fontSize: "clamp(1.6rem, 5.2vw, 4.2rem)" }}
                >
                  {v.label}
                </span>
              </div>
              <div className="flex items-center gap-3 sm:gap-5 shrink-0">
                <span
                  className="text-2xl sm:text-4xl select-none transition-transform group-hover:translate-x-1 group-hover:-translate-y-0.5"
                  aria-hidden
                >
                  {v.emoji}
                </span>
                <span
                  className="font-flyer text-2xl sm:text-4xl text-white/25 group-hover:text-[#C6FF00] transition-colors leading-none"
                  aria-hidden
                >
                  →
                </span>
              </div>
            </motion.button>
          ))}
        </div>
      </motion.div>

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
