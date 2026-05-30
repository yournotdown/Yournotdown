import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { trackEvent } from "../lib/api";

// Slugs stay stable for analytics — only the labels evolve.
const VIBES = [
  { slug: "just-vibing", emoji: "😇", label: "Take It Easy" },
  { slug: "down", emoji: "😏", label: "Let's See Where This Goes" },
  { slug: "very-down", emoji: "🔥", label: "Let's Make It Count" },
  { slug: "send-it", emoji: "🚀", label: "No Regrets" },
];

export default function VibePage() {
  const navigate = useNavigate();

  const handleSelect = (vibe) => {
    trackEvent("vibe_click", { vibe: vibe.slug });
    navigate(`/tonight?vibe=${vibe.slug}`);
  };

  return (
    <div
      className="min-h-screen px-6 pt-8 pb-16 bg-[#050505] relative overflow-hidden"
      data-testid="vibe-page"
    >
      {/* Ambient drifting glows */}
      <motion.div
        className="pointer-events-none absolute -top-40 left-1/3 w-[520px] h-[520px] rounded-full bg-[#7C3AED]/12 blur-[160px]"
        animate={{ x: [0, 40, -20, 0], y: [0, 30, -10, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="pointer-events-none absolute -bottom-40 -right-20 w-[420px] h-[420px] rounded-full bg-[#A855F7]/8 blur-[140px]"
        animate={{ x: [0, -30, 15, 0], y: [0, -25, 10, 0] }}
        transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="pointer-events-none absolute inset-0 grain opacity-30" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_45%,_#000_100%)]" />

      <div className="max-w-2xl mx-auto relative z-10">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-white/40 hover:text-white/80 text-xs uppercase tracking-[0.2em] mb-6 transition-colors"
          data-testid="vibe-back-button"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </button>

        <motion.h1
          className="font-display font-black text-white text-4xl sm:text-5xl md:text-6xl leading-[0.95] tracking-tight"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          data-testid="vibe-headline"
        >
          How down<br />are you?
        </motion.h1>

        <motion.p
          className="mt-2 text-[#A1A1AA] text-sm tracking-wide"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.25, duration: 0.6 }}
          data-testid="vibe-subhead"
        >
          Tonight starts here.
        </motion.p>

        <div className="grid grid-cols-2 gap-3 sm:gap-4 mt-6">
          {VIBES.map((v, i) => (
            <motion.button
              key={v.slug}
              onClick={() => handleSelect(v)}
              initial={{ opacity: 0, y: 18, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: 0.15 + i * 0.07, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              whileTap={{ scale: 0.97 }}
              whileHover={{ y: -6 }}
              className="group relative h-44 sm:h-52 flex flex-col items-center justify-center px-3 pt-4 pb-5 bg-[#121218] hover:bg-[#1A1A22] border border-white/[0.06] hover:border-[#7C3AED]/40 rounded-[28px] transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[#7C3AED]/60 overflow-hidden"
              data-testid={`vibe-btn-${v.slug}`}
            >
              {/* hover aura */}
              <span
                aria-hidden
                className="pointer-events-none absolute -bottom-20 left-1/2 -translate-x-1/2 w-56 h-56 rounded-full bg-[#7C3AED]/0 group-hover:bg-[#7C3AED]/20 blur-3xl transition-colors duration-500"
              />
              <motion.span
                className="relative text-8xl sm:text-9xl select-none leading-none drop-shadow-[0_8px_24px_rgba(124,58,237,0.25)]"
                aria-hidden
                animate={{ y: [0, -4, 0] }}
                transition={{ duration: 4 + i * 0.4, repeat: Infinity, ease: "easeInOut" }}
              >
                {v.emoji}
              </motion.span>
              <span className="relative mt-2 text-[11px] sm:text-xs font-bold text-white text-center tracking-[0.08em] leading-tight px-1 uppercase">
                {v.label}
              </span>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
