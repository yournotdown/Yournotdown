import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { api, trackEvent } from "../lib/api";

export default function CategoriesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const vibe = searchParams.get("vibe");
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/categories")
      .then((r) => {
        setCategories(r.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleCategory = (slug) => {
    trackEvent("category_click", { category_slug: slug });
    const qs = vibe ? `?vibe=${vibe}` : "";
    navigate(`/c/${slug}${qs}`);
  };

  return (
    <div className="min-h-screen px-6 py-10 bg-[#050505] relative overflow-hidden" data-testid="categories-page">
      <div className="pointer-events-none absolute -top-40 right-0 w-[500px] h-[500px] rounded-full bg-[#C6FF00]/15 blur-[140px]" />

      <div className="max-w-2xl mx-auto relative z-10">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-white/60 hover:text-white text-sm mb-10 transition-colors"
          data-testid="categories-back-button"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <motion.h1
          className="font-display font-black text-white text-4xl sm:text-5xl md:text-6xl leading-[0.95] tracking-tight"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          data-testid="categories-headline"
        >
          What's<br />the move?
        </motion.h1>

        <p className="mt-3 text-[#A1A1AA] text-base">Pick a vibe. We've got you.</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-10">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="aspect-square rounded-3xl bg-[#121218] animate-pulse" />
              ))
            : categories.map((cat, i) => (
                <motion.button
                  key={cat.slug}
                  onClick={() => handleCategory(cat.slug)}
                  initial={{ opacity: 0, y: 20, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ delay: i * 0.05, duration: 0.4 }}
                  whileTap={{ scale: 0.95 }}
                  whileHover={{ y: -4, backgroundColor: "#1A1A22" }}
                  className="flex flex-col items-center justify-center aspect-square p-4 bg-[#121218] border border-white/5 hover:border-white/15 rounded-3xl transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#C6FF00]"
                  data-testid={`category-btn-${cat.slug}`}
                >
                  <span className="text-5xl sm:text-6xl mb-3 select-none" aria-hidden>
                    {cat.emoji}
                  </span>
                  <span className="text-sm sm:text-base font-bold text-white text-center">
                    {cat.name}
                  </span>
                </motion.button>
              ))}
        </div>
      </div>
    </div>
  );
}
