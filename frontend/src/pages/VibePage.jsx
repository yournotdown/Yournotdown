import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { trackEvent } from "../lib/api";

const VIBES = [
  { slug: "just-vibing", emoji: "😇", label: "Just Vibing" },
  { slug: "down", emoji: "😏", label: "Down" },
  { slug: "very-down", emoji: "🔥", label: "Very Down" },
  { slug: "send-it", emoji: "🚀", label: "Send It" },
];

export default function VibePage() {
  const navigate = useNavigate();

  const handleSelect = (vibe) => {
    trackEvent("vibe_click", { vibe: vibe.slug });
    navigate(`/tonight?vibe=${vibe.slug}`);
  };

  return (
    <div className="min-h-screen px-6 py-10 bg-[#050505] relative overflow-hidden" data-testid="vibe-page">
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#FF2A5F]/15 blur-[160px]" />

      <div className="max-w-2xl mx-auto relative z-10">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 text-white/60 hover:text-white text-sm mb-10 transition-colors"
          data-testid="vibe-back-button"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <motion.h1
          className="font-display font-black text-white text-4xl sm:text-5xl md:text-6xl leading-[0.95] tracking-tight"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          data-testid="vibe-headline"
        >
          How down<br />are you?
        </motion.h1>

        <p className="mt-3 text-[#A1A1AA] text-base">Be honest. We won't tell.</p>

        <div className="grid grid-cols-2 gap-4 mt-10">
          {VIBES.map((v, i) => (
            <motion.button
              key={v.slug}
              onClick={() => handleSelect(v)}
              initial={{ opacity: 0, y: 20, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: i * 0.06, duration: 0.4 }}
              whileTap={{ scale: 0.95 }}
              whileHover={{ y: -4 }}
              className="flex flex-col items-center justify-center aspect-square p-4 bg-[#121212] border border-white/5 hover:border-white/15 hover:bg-[#1A1A1A] rounded-3xl transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#FF2A5F]"
              data-testid={`vibe-btn-${v.slug}`}
            >
              <span className="text-6xl sm:text-7xl mb-3 select-none" aria-hidden>
                {v.emoji}
              </span>
              <span className="text-base sm:text-lg font-bold text-white text-center">
                {v.label}
              </span>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
