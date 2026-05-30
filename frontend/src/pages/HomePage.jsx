import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { trackEvent } from "../lib/api";

export default function HomePage() {
  const navigate = useNavigate();

  useEffect(() => {
    trackEvent("homepage_visit");
  }, []);

  const handleClick = () => {
    trackEvent("im_down_click");
    navigate("/vibe");
  };

  return (
    <div
      className="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden bg-[#050505]"
      data-testid="homepage"
    >
      {/* Atmospheric depth */}
      <div className="pointer-events-none absolute inset-0 grain opacity-40" />
      <div className="pointer-events-none absolute -top-48 left-1/2 -translate-x-1/2 w-[720px] h-[720px] rounded-full bg-[#7C3AED]/12 blur-[180px]" />
      <div className="pointer-events-none absolute bottom-[-15%] right-[-10%] w-[480px] h-[480px] rounded-full bg-[#A855F7]/8 blur-[160px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_40%,_#000_100%)]" />

      <motion.div
        className="relative z-10 w-full max-w-2xl text-center flex flex-col items-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <motion.h1
          className="font-display font-black text-white text-5xl sm:text-7xl md:text-8xl leading-[0.92] tracking-tight"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.9 }}
          data-testid="homepage-headline"
        >
          YOU'RE<br />NOT<br />
          <span className="bg-gradient-to-b from-[#A855F7] to-[#7C3AED] bg-clip-text text-transparent">
            DOWN?
          </span>
        </motion.h1>

        <motion.button
          onClick={handleClick}
          className="group relative mt-16 w-full max-w-sm py-6 px-8 text-white text-lg sm:text-xl font-bold rounded-full btn-glass-violet animate-pulse-violet flex items-center justify-center gap-3 transition-all overflow-hidden"
          initial={{ opacity: 0, y: 16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.7, type: "spring", stiffness: 140 }}
          whileTap={{ scale: 0.97 }}
          whileHover={{ scale: 1.02 }}
          data-testid="homepage-im-down-button"
        >
          {/* Sheen on hover */}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-0 group-hover:opacity-100 group-hover:translate-x-full -translate-x-full transition-all duration-700"
          />
          <span className="relative tracking-[0.18em]">I'M DOWN</span>
          <ArrowRight className="relative w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </motion.button>
      </motion.div>

      <button
        onClick={() => navigate("/admin/login")}
        className="absolute bottom-6 right-6 text-[10px] uppercase tracking-[0.2em] text-white/20 hover:text-white/50 transition-colors"
        data-testid="homepage-admin-link"
      >
        admin
      </button>
    </div>
  );
}
