import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Phone, Navigation, Globe, Flame } from "lucide-react";
import { api, trackEvent, resolveImageUrl } from "../lib/api";

export default function CategoryDetailPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [businesses, setBusinesses] = useState([]);
  const [category, setCategory] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/categories").then((r) => r.data),
      api.get("/businesses", { params: { category: slug, city: "nashville" } }).then((r) => r.data),
    ])
      .then(([cats, biz]) => {
        const cat = cats.find((c) => c.slug === slug);
        setCategory(cat || { slug, name: slug, emoji: "✨" });
        setBusinesses(biz);
        biz.forEach((b) => trackEvent("business_view", { business_id: b.id, category_slug: slug }));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [slug]);

  const directionsUrl = (b) => {
    const q = encodeURIComponent(b.address || b.name);
    return `https://www.google.com/maps/search/?api=1&query=${q}`;
  };

  const handleAction = (type, b) => {
    trackEvent(type, { business_id: b.id, category_slug: slug });
  };

  return (
    <div className="min-h-screen bg-[#050505] pb-24" data-testid="category-detail-page">
      <div className="max-w-2xl mx-auto px-6 pt-10">
        <button
          onClick={() => navigate("/categories")}
          className="flex items-center gap-2 text-white/60 hover:text-white text-sm mb-8 transition-colors"
          data-testid="category-detail-back"
        >
          <ArrowLeft className="w-4 h-4" />
          Categories
        </button>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-10"
        >
          <div className="text-6xl mb-4" aria-hidden>
            {category?.emoji}
          </div>
          <h1 className="font-display font-black text-white text-4xl sm:text-5xl tracking-tight leading-none" data-testid="category-detail-title">
            {category?.name}
          </h1>
          <p className="mt-3 text-[#A1A1AA] text-base">
            {businesses.length} {businesses.length === 1 ? "spot" : "spots"} in Nashville.
          </p>
        </motion.div>

        {loading ? (
          <div className="space-y-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-[420px] rounded-[32px] bg-[#121212] animate-pulse" />
            ))}
          </div>
        ) : businesses.length === 0 ? (
          <div className="text-center text-[#A1A1AA] py-20" data-testid="category-empty-state">
            Nothing here yet. Check back soon.
          </div>
        ) : (
          <div className="space-y-8">
            {businesses.map((b, i) => (
              <motion.div
                key={b.id}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.45 }}
                className="bg-[#121212] rounded-[32px] overflow-hidden border border-white/10 shadow-2xl group"
                data-testid={`business-card-${b.id}`}
              >
                <div className="relative w-full h-72 bg-[#1A1A1A] overflow-hidden">
                  {resolveImageUrl(b) && (
                    <img
                      src={resolveImageUrl(b)}
                      alt={b.name}
                      className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                      loading="lazy"
                    />
                  )}
                  {b.featured && (
                    <div className="absolute top-4 left-4 px-3 py-1.5 bg-[#FF2A5F] text-white text-xs font-bold rounded-full flex items-center gap-1.5" data-testid={`featured-badge-${b.id}`}>
                      <Flame className="w-3 h-3" />
                      FEATURED
                    </div>
                  )}
                </div>
                <div className="p-6">
                  <h3 className="font-display text-2xl sm:text-3xl font-bold text-white" data-testid={`business-name-${b.id}`}>
                    {b.name}
                  </h3>
                  <p className="mt-2 text-[#A1A1AA] text-sm leading-relaxed line-clamp-3">
                    {b.description}
                  </p>
                  <div className="grid grid-cols-3 gap-3 mt-6">
                    {b.phone ? (
                      <a
                        href={`tel:${b.phone}`}
                        onClick={() => handleAction("phone_click", b)}
                        className="py-4 rounded-full bg-white/5 hover:bg-white/10 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95"
                        data-testid={`business-call-${b.id}`}
                      >
                        <Phone className="w-4 h-4" />
                        <span className="hidden sm:inline">Call</span>
                      </a>
                    ) : <div />}
                    {b.address || b.name ? (
                      <a
                        href={directionsUrl(b)}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => handleAction("directions_click", b)}
                        className="py-4 rounded-full bg-white/5 hover:bg-white/10 text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95"
                        data-testid={`business-directions-${b.id}`}
                      >
                        <Navigation className="w-4 h-4" />
                        <span className="hidden sm:inline">Directions</span>
                      </a>
                    ) : <div />}
                    {b.website ? (
                      <a
                        href={b.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => handleAction("website_click", b)}
                        className="py-4 rounded-full bg-[#FF2A5F] hover:bg-[#E01E50] text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95 glow-pink"
                        data-testid={`business-website-${b.id}`}
                      >
                        <Globe className="w-4 h-4" />
                        <span className="hidden sm:inline">Website</span>
                      </a>
                    ) : <div />}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
