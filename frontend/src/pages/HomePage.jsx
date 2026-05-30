import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { trackEvent } from "../lib/api";

const MARQUEE = "NO BORING NIGHTS";

export default function HomePage() {
  const navigate = useNavigate();
  const [crashing, setCrashing] = useState(false);

  useEffect(() => {
    trackEvent("homepage_visit");
  }, []);

  const handleClick = () => {
    if (crashing) return;
    trackEvent("im_down_click");
    setCrashing(true);
    setTimeout(() => navigate("/vibe"), 420);
  };

  return (
    <div
      className="relative min-h-screen bg-black text-white overflow-hidden"
      data-testid="homepage"
    >
      {/* Background layers */}
      <div className="pointer-events-none absolute inset-0 film-grain opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_55%,_#000_100%)]" />
      <div className="pointer-events-none absolute inset-0 strobe-dim bg-black" />
      {/* Scanline */}
      <div className="pointer-events-none absolute inset-x-0 h-px bg-white/40 scanline-anim" />

      {/* "Crash" inversion flash on click */}
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

      {/* HERO TYPE */}
      <motion.div
        className="relative z-10 min-h-screen flex flex-col justify-center px-6 sm:px-10 pb-24 pt-24"
        initial={{ opacity: 0, y: 14 }}
        animate={crashing ? { scale: 0.92, opacity: 0 } : { opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: crashing ? 0.32 : 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.h2
          className="font-flyer flicker-neon text-white uppercase select-none"
          style={{
            fontSize: "clamp(2.5rem, 8.5vw, 7rem)",
            transform: "rotate(-1.5deg) translateX(-1%)",
            transformOrigin: "left",
          }}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          data-testid="homepage-headline"
        >
          You're not down?
        </motion.h2>

        <motion.button
          onClick={handleClick}
          className="group relative font-flyer text-white uppercase select-none text-left bg-transparent border-0 p-0 mt-2 sm:mt-3 cursor-pointer focus:outline-none"
          style={{
            fontSize: "clamp(7rem, 28vw, 22rem)",
          }}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
          whileHover={{ x: 4 }}
          whileTap={{ scale: 0.985 }}
          data-testid="homepage-im-down-button"
          aria-label="I'm Down — start tonight"
        >
          {/* Letters — invert on hover */}
          <span className="relative inline-block transition-colors duration-150 group-hover:text-[#C6FF00]">
            I'M DOWN
          </span>
          <span className="lime-dot inline-block ml-1 sm:ml-2">.</span>
        </motion.button>
      </motion.div>

      {/* MARQUEE STRIP */}
      <div
        className="absolute bottom-0 inset-x-0 z-10 border-t border-white/10 bg-black/80 backdrop-blur-sm overflow-hidden"
        data-testid="homepage-marquee"
      >
        <div className="marquee-track flex whitespace-nowrap py-3 sm:py-4">
          {Array.from({ length: 16 }).map((_, i) => (
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

      {/* CORNER MARKS */}
      <div className="absolute top-5 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        YND
        <span className="lime-dot mx-1.5">/</span>
        EST. 26
      </div>
      <div className="absolute top-5 right-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        Vol. 001
      </div>

      <button
        onClick={() => navigate("/admin/login")}
        className="absolute bottom-16 right-6 z-20 text-[10px] uppercase tracking-[0.3em] text-white/20 hover:text-[#C6FF00] transition-colors"
        data-testid="homepage-admin-link"
      >
        admin
      </button>
    </div>
  );
}
