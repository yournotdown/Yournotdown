import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Phone, Navigation, Globe, Flame, ExternalLink } from "lucide-react";
import { api, formatEventSchedule, matchedEventsForBusinesses, trackEvent, resolveImageUrl } from "../lib/api";
import { activeCitySlug } from "../lib/cities";
import EventCard from "../components/EventCard";

export default function CategoryDetailPage() {
  const { citySlug: routeCitySlug, slug } = useParams();
  const citySlug = activeCitySlug(routeCitySlug);
  const navigate = useNavigate();
  const [businesses, setBusinesses] = useState([]);
  const [events, setEvents] = useState([]);
  const [category, setCategory] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/categories").then((r) => r.data),
      api.get("/businesses", { params: { category: slug, city: citySlug } }).then((r) => r.data),
    ])
      .then(([cats, biz]) => {
        const cat = cats.find((c) => c.slug === slug);
        setCategory(cat || { slug, name: slug, emoji: "✨" });
        setBusinesses(biz);
        setEvents(matchedEventsForBusinesses(biz));
        // One view event per business per page-load (not per render)
        const seen = new Set();
        biz.forEach((b) => {
          if (!seen.has(b.id)) {
            seen.add(b.id);
            trackEvent("business_view", { business_id: b.id, category_slug: slug, city_slug: citySlug });
          }
        });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [citySlug, slug]);

  const directionsUrl = (b) => {
    const q = encodeURIComponent(b.address || b.name);
    return `https://www.google.com/maps/search/?api=1&query=${q}`;
  };

  const handleAction = (type, b) => {
    trackEvent(type, { business_id: b.id, category_slug: slug, city_slug: citySlug });
  };

  return (
    <div className="min-h-screen bg-[#050505] pb-24" data-testid="category-detail-page">
      <div className="max-w-2xl mx-auto px-6 pt-10">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-white/60 hover:text-white text-sm mb-8 transition-colors"
          data-testid="category-detail-back"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
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
            {businesses.length} {businesses.length === 1 ? "spot" : "spots"} for you.
          </p>
        </motion.div>

        {loading ? (
          <div className="space-y-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-[420px] rounded-[32px] bg-[#121218] animate-pulse" />
            ))}
          </div>
        ) : (
          <>
            <section className="mb-14" data-testid="tonights-events-section">
              {slug === "live-music" && (
                <>
                  <div className="mb-5 border-t border-white/10 pt-5">
                    <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">
                      Live calendar
                    </div>
                    <h2 className="mt-2 font-flyer text-3xl uppercase text-white">
                      Tonight's Shows<span className="lime-dot">.</span>
                    </h2>
                  </div>

                  {events.length === 0 ? (
                    <p className="border border-white/10 bg-[#121218] px-5 py-6 text-sm text-[#A1A1AA]">
                      No matched live music shows listed for tonight.
                    </p>
                  ) : (
                    <div className="space-y-4">
                      {events.map((event, i) => (
                        <EventCard key={event.id || event.external_event_id} event={event} index={i} />
                      ))}
                    </div>
                  )}
                </>
              )}
            </section>

            <section data-testid="venue-list-section">
              <div className="mb-5 border-t border-white/10 pt-5">
                <div className="text-[10px] uppercase tracking-[0.3em] text-white/40">
                  Explore the city
                </div>
                <h2 className="mt-2 font-flyer text-3xl uppercase text-white">
                  Venues<span className="lime-dot">.</span>
                </h2>
              </div>

              {businesses.length === 0 ? (
                <div className="text-center text-[#A1A1AA] py-20" data-testid="category-empty-state">
                  Nothing here yet. Check back soon.
                </div>
              ) : (
                <div className="space-y-8">
                  {businesses.map((b, i) => {
                    const eventSchedule = formatEventSchedule(b.event);
                    const businessImageUrl = resolveImageUrl(b, { maxWidth: 960 });
                    return (
                    <motion.div
                      key={b.id}
                      initial={{ opacity: 0, y: 24 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06, duration: 0.45 }}
                      className="bg-[#121218] rounded-[32px] overflow-hidden border border-white/10 shadow-2xl group"
                      data-testid={`business-card-${b.id}`}
                    >
                      <div className="relative w-full h-72 bg-[#1A1A22] overflow-hidden">
                        {businessImageUrl && (
                          <img
                            src={businessImageUrl}
                            alt={b.name}
                            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                            loading="lazy"
                            decoding="async"
                            sizes="(min-width: 768px) 768px, 100vw"
                          />
                        )}
                        {b.featured && (
                          <div className="absolute top-4 left-4 px-3 py-1.5 bg-[#C6FF00] text-white text-xs font-bold rounded-full flex items-center gap-1.5" data-testid={`featured-badge-${b.id}`}>
                            <Flame className="w-3 h-3" />
                            FEATURED
                          </div>
                        )}
                      </div>
                      <div className="p-6">
                        <h3 className="font-display text-2xl sm:text-3xl font-bold text-white" data-testid={`business-name-${b.id}`}>
                          {b.name}
                        </h3>
                        {b.event && (
                          <div className="mt-4 border-l-2 border-[#C6FF00] pl-3" data-testid={`business-event-${b.id}`}>
                            <div className="text-[10px] uppercase tracking-[0.24em] text-[#C6FF00]">
                              Tonight: {b.event.title}
                            </div>
                            <div className="mt-1 text-xs uppercase tracking-[0.16em] text-white/55">
                              {[eventSchedule, b.event.venue_name].filter(Boolean).join(" · ")}
                            </div>
                          </div>
                        )}
                        <p className="mt-2 text-[#A1A1AA] text-sm leading-relaxed line-clamp-3">
                          {b.description}
                        </p>
                        <div className={`grid gap-3 mt-6 ${b.event?.ticket_url ? "grid-cols-2 sm:grid-cols-4" : "grid-cols-3"}`}>
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
                              className="py-4 rounded-full bg-[#C6FF00] hover:bg-[#A8E000] text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95 glow-lime"
                              data-testid={`business-website-${b.id}`}
                            >
                              <Globe className="w-4 h-4" />
                              <span className="hidden sm:inline">Website</span>
                            </a>
                          ) : <div />}
                          {b.event?.ticket_url ? (
                            <a
                              href={b.event.ticket_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={() => handleAction("ticket_click", b)}
                              className="py-4 rounded-full bg-[#C6FF00] hover:bg-white text-black text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-colors active:scale-95"
                              data-testid={`business-tickets-${b.id}`}
                            >
                              <ExternalLink className="w-4 h-4" />
                              <span className="hidden sm:inline">Buy Tickets</span>
                              <span className="sm:hidden">Tickets</span>
                            </a>
                          ) : null}
                        </div>
                      </div>
                    </motion.div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
