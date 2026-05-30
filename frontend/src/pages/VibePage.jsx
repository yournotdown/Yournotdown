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
      {/* Atmospherics — same as homepage */}
      <div className="pointer-events-none absolute inset-0 film-grain opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_55%,_#000_100%)]" />
      <div className="pointer-events-none absolute inset-0 strobe-dim bg-black" />
      <div className="pointer-events-none absolute inset-x-0 h-px bg-white/40 scanline-anim" />

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

      {/* Content — playful, emoji-first */}
      <motion.div
        className="relative z-10 min-h-screen flex flex-col justify-center pt-24 pb-28 px-5 sm:px-10 max-w-5xl mx-auto w-full"
        animate={crashing ? { scale: 0.96, opacity: 0 } : { scale: 1, opacity: 1 }}
        transition={{ duration: 0.32 }}
      >
        <motion.h1
          className="font-flyer text-white uppercase"
          style={{
            fontSize: "clamp(2rem, 6vw, 4.5rem)",
            transform: "rotate(-1.5deg)",
            transformOrigin: "left",
          }}
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55 }}
          data-testid="vibe-headline"
        >
          How down<br />are you<span className="lime-dot">?</span>
        </motion.h1>

        <div className="mt-8 sm:mt-12 grid grid-cols-2 gap-3 sm:gap-5">
          {VIBES.map((v, i) => (
            <motion.button
              key={v.slug}
              onClick={() => handleSelect(v)}
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.07, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              whileTap={{ scale: 0.95 }}
              whileHover={{ y: -6 }}
              className="group relative aspect-square sm:aspect-[5/4] bg-[#0A0A0A] border border-white/10 hover:border-[#C6FF00]/60 hover:bg-[#0C0F08] flex flex-col items-center justify-center px-3 py-5 cursor-pointer transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#C6FF00]/60 overflow-hidden"
              data-testid={`vibe-btn-${v.slug}`}
            >
              {/* Hover lime aura behind emoji */}
              <span
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full bg-[#C6FF00]/0 group-hover:bg-[#C6FF00]/12 blur-3xl transition-colors duration-500"
              />
              {/* Tiny index */}
              <span className="absolute top-3 left-3 font-flyer text-[10px] uppercase tracking-[0.3em] text-white/30 tabular-nums">
                {String(i + 1).padStart(2, "0")}
              </span>

              {/* GIANT EMOJI — the hero */}
              <motion.span
                className="relative select-none leading-none drop-shadow-[0_8px_24px_rgba(198,255,0,0.18)]"
                aria-hidden
                style={{ fontSize: "clamp(5rem, 18vw, 10rem)" }}
                animate={{ y: [0, -5, 0], rotate: [0, i % 2 === 0 ? 2 : -2, 0] }}
                transition={{
                  duration: 4 + i * 0.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              >
                {v.emoji}
              </motion.span>

              {/* Small caption */}
              <span className="relative mt-2 sm:mt-3 font-flyer text-[11px] sm:text-sm uppercase tracking-[0.18em] text-white group-hover:text-[#C6FF00] transition-colors text-center leading-tight">
                {v.label}
              </span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Marquee */}
      <div className="absolute bottom-0 inset-x-0 z-10 border-t border-white/10 bg-black/80 backdrop-blur-sm overflow-hidden">
        <div className="marquee-track flex whitespace-nowrap py-3 sm:py-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <span
              key={`marquee-${i}`}
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
