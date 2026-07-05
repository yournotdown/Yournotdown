import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { trackEvent } from "../lib/api";
import { activeCitySlug, cityDisplayName, cityPath } from "../lib/cities";

const MARQUEE = "NO BORING NIGHTS";

export default function HomePage() {
  const navigate = useNavigate();
  const { citySlug: routeCitySlug } = useParams();
  const citySlug = activeCitySlug(routeCitySlug);
  const [crashing, setCrashing] = useState(false);

  useEffect(() => {
    trackEvent("homepage_visit", { city_slug: citySlug });
  }, [citySlug]);

  const handleClick = () => {
    if (crashing) return;
    trackEvent("im_down_click", { city_slug: citySlug });
    setCrashing(true);
    setTimeout(() => navigate(cityPath(citySlug, "vibe")), 240);
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

      {/* HERO TYPE */}
      <motion.div
        className="relative z-10 min-h-[100svh] flex flex-col justify-center px-6 sm:px-10 pb-28 pt-24 md:pt-28"
        initial={{ opacity: 0, y: 14 }}
        animate={crashing ? { scale: 0.98, opacity: 0 } : { opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: crashing ? 0.24 : 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mx-auto flex w-full max-w-[1200px] flex-col justify-center lg:min-h-[calc(100svh-8rem)] lg:justify-center">
          <motion.h2
            className="font-flyer flicker-neon text-white uppercase select-none max-w-[11ch]"
            style={{
              fontSize: "clamp(2.5rem, 5.6vw, 5.75rem)",
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
            className="group relative mt-3 bg-transparent p-0 text-left font-flyer uppercase text-white select-none cursor-pointer focus:outline-none md:mt-4 lg:max-w-[1100px]"
            style={{
              fontSize: "clamp(5rem, 15vw, 12.5rem)",
            }}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.75, delay: 0.18, ease: [0.22, 1, 0.36, 1] }}
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.985 }}
            data-testid="homepage-im-down-button"
            aria-label="I'm Down — start tonight"
          >
            <span className="relative inline-block transition-colors duration-150 group-hover:text-[#C6FF00]">
              I'M DOWN
            </span>
            <span className="lime-dot inline-block ml-1 sm:ml-2">.</span>
            <span className="mt-3 block font-display text-[11px] tracking-[0.32em] text-white/65 sm:text-sm md:text-base lg:mt-4 lg:text-lg">
              {cityDisplayName(citySlug)}
            </span>
          </motion.button>
        </div>
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
