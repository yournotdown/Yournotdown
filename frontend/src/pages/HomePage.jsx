import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { api, trackEvent } from "../lib/api";

export default function HomePage() {
  const navigate = useNavigate();
  const [city, setCity] = useState({ name: "Nashville", slug: "nashville" });

  useEffect(() => {
    trackEvent("homepage_visit");
    api
      .get("/cities/default")
      .then((r) => setCity(r.data))
      .catch(() => {});
  }, []);

  const handleClick = () => {
    trackEvent("im_down_click", { city_slug: city.slug });
    navigate("/categories");
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden bg-[#050505]" data-testid="homepage">
      {/* Background glow */}
      <div className="pointer-events-none absolute inset-0 grain opacity-50" />
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-[#FF2A5F]/20 blur-[160px]" />
      <div className="pointer-events-none absolute bottom-0 right-0 w-[400px] h-[400px] rounded-full bg-[#FF2A5F]/10 blur-[140px]" />

      <motion.div
        className="relative z-10 w-full max-w-2xl text-center flex flex-col items-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <motion.h1
          className="font-display font-black text-white text-5xl sm:text-7xl md:text-8xl leading-[0.92] tracking-tight"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.7 }}
          data-testid="homepage-headline"
        >
          YOU'RE<br />NOT<br />
          <span className="text-[#FF2A5F]">DOWN?</span>
        </motion.h1>

        <motion.p
          className="mt-8 text-lg sm:text-xl text-[#A1A1AA] font-medium"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          data-testid="homepage-subheadline"
        >
          Let's find out.
        </motion.p>

        <motion.button
          onClick={handleClick}
          className="group mt-14 w-full max-w-sm py-6 px-8 bg-[#FF2A5F] hover:bg-[#E01E50] text-white text-lg sm:text-xl font-bold rounded-full glow-pink flex items-center justify-center gap-3 transition-colors"
          initial={{ opacity: 0, y: 16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.5, type: "spring", stiffness: 200 }}
          whileTap={{ scale: 0.96 }}
          whileHover={{ scale: 1.03 }}
          data-testid="homepage-im-down-button"
        >
          <span className="tracking-wide">I'M DOWN {city.name.toUpperCase()}</span>
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </motion.button>
      </motion.div>

      <button
        onClick={() => navigate("/admin/login")}
        className="absolute bottom-6 right-6 text-xs text-white/30 hover:text-white/60 transition-colors"
        data-testid="homepage-admin-link"
      >
        admin
      </button>
    </div>
  );
}
