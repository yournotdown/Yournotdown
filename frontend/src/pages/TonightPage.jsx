import { useEffect, useState, useCallback } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Phone, Navigation, Globe, RotateCw, ExternalLink } from "lucide-react";
import { api, formatEventTime, trackEvent, resolveImageUrl } from "../lib/api";
import { activeCitySlug, cityPath } from "../lib/cities";

const VIBE_LABELS = {
  "just-vibing": { emoji: "😇", label: "Take It Easy" },
  down: { emoji: "😏", label: "Let's See Where This Goes" },
  "very-down": { emoji: "🔥", label: "Let's Make It Count" },
  "send-it": { emoji: "🚀", label: "No Regrets" },
};

const SLOT_TITLES = {
  dinner: "DINNER",
  drinks: "DRINKS",
  entertainment: "LIVE MUSIC",
  "late-night": "LATE NIGHT",
};

const MARQUEE = "WHAT'S NEXT";

export default function TonightPage() {
  const navigate = useNavigate();
  const { citySlug: routeCitySlug } = useParams();
  const citySlug = activeCitySlug(routeCitySlug);
  const [searchParams] = useSearchParams();
  const vibe = searchParams.get("vibe") || "down";
  const vibeMeta = VIBE_LABELS[vibe] || { emoji: "✨", label: vibe };

  const [itinerary, setItinerary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [seenIds, setSeenIds] = useState([]);
  const [refreshCount, setRefreshCount] = useState(0);
  const [lastTicketmasterEventIds, setLastTicketmasterEventIds] = useState([]);
  const [lockedSteps, setLockedSteps] = useState({});
  const [regenerating, setRegenerating] = useState(false);
  const [saveOverlayOpen, setSaveOverlayOpen] = useState(false);
  const [saveOverlayDismissed, setSaveOverlayDismissed] = useState(false);
  const [email, setEmail] = useState("");
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState("");
  const [saveError, setSaveError] = useState("");
  const sponsorship = itinerary?.tonight_move_sponsorship;
  const allStepsLocked = Boolean(
    itinerary?.steps?.length === 4 && itinerary.steps.every((step) => Boolean(lockedSteps[step.slot]))
  );

  const generate = useCallback(
    async ({
      excludeIds = [],
      excludeEventIds = [],
      liveMusicEventMode = "normal",
      lockedStepsBySlot = {},
      scrollToTopOnSuccess = false,
    } = {}) => {
      setError(null);
      try {
        const r = await api.post("/itinerary/generate", {
          vibe,
          city: citySlug,
          exclude_ids: excludeIds,
          exclude_event_ids: excludeEventIds,
          live_music_event_mode: liveMusicEventMode,
          locked_steps: lockedStepsBySlot,
        });
        setItinerary(r.data);
        trackEvent("itinerary_view", { vibe, itinerary_id: r.data.id, city_slug: citySlug });
        const lockedSlots = new Set(Object.keys(lockedStepsBySlot));
        const nextLockedSteps = {};
        r.data.steps.forEach((step) => {
          if (lockedSlots.has(step.slot)) {
            nextLockedSteps[step.slot] = step;
          }
        });
        setLockedSteps(nextLockedSteps);
        const newIds = r.data.steps
          .filter((step) => !lockedSlots.has(step.slot))
          .map((s) => s.business?.id)
          .filter(Boolean);
        const liveMusicStep = r.data.steps.find((step) => step.slot === "entertainment");
        const liveMusicEvent = liveMusicStep?.event;
        const liveMusicEventId = liveMusicEvent?.external_event_id || liveMusicEvent?.id;
        const entertainmentLocked = lockedSlots.has("entertainment");
        setSeenIds(newIds);
        if (!entertainmentLocked && liveMusicEvent?.source === "ticketmaster" && liveMusicEventId) {
          setLastTicketmasterEventIds([liveMusicEventId]);
        } else if (!entertainmentLocked && liveMusicEventMode === "ticketmaster") {
          setLastTicketmasterEventIds([]);
        }
        if (scrollToTopOnSuccess && typeof window !== "undefined") {
          window.requestAnimationFrame(() => {
            window.scrollTo({ top: 0, behavior: "smooth" });
          });
        }
      } catch (e) {
        setError(e?.response?.data?.detail || "Couldn't plan tonight. Try again.");
      } finally {
        setLoading(false);
        setRegenerating(false);
      }
    },
    [citySlug, vibe]
  );

  useEffect(() => {
    setLoading(true);
    setSeenIds([]);
    setRefreshCount(0);
    setLastTicketmasterEventIds([]);
    setLockedSteps({});
    setSaveOverlayOpen(false);
    setSaveOverlayDismissed(false);
    setEmail("");
    setSaveLoading(false);
    setSaveSuccess("");
    setSaveError("");
    generate({ liveMusicEventMode: "ticketmaster_preferred" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [citySlug, vibe]);

  useEffect(() => {
    if (allStepsLocked) {
      if (!saveOverlayDismissed && !saveSuccess) {
        setSaveOverlayOpen(true);
      }
      return;
    }
    setSaveOverlayDismissed(false);
    setSaveOverlayOpen(false);
  }, [allStepsLocked, saveOverlayDismissed, saveSuccess]);

  const handleAnother = () => {
    setRegenerating(true);
    trackEvent("another_night_click", { vibe, city_slug: citySlug });
    const nextRefreshCount = refreshCount + 1;
    const liveMusicEventMode = nextRefreshCount % 4 === 0 ? "ticketmaster" : "normal";
    const unlockedCurrentIds = (itinerary?.steps || [])
      .filter((step) => !lockedSteps[step.slot])
      .map((step) => step.business?.id)
      .filter(Boolean);
    setRefreshCount(nextRefreshCount);
    generate({
      excludeIds: unlockedCurrentIds.length > 0 ? unlockedCurrentIds : seenIds,
      excludeEventIds: liveMusicEventMode === "ticketmaster" ? lastTicketmasterEventIds : [],
      liveMusicEventMode,
      lockedStepsBySlot: lockedSteps,
      scrollToTopOnSuccess: true,
    });
  };

  const handleLockStep = (step) => {
    setSaveError("");
    setLockedSteps((prev) => ({ ...prev, [step.slot]: step }));
  };

  const handleUnlockStep = (slot) => {
    setSaveSuccess("");
    setSaveError("");
    setLockedSteps((prev) => {
      const next = { ...prev };
      delete next[slot];
      return next;
    });
  };

  const closeSaveOverlay = () => {
    setSaveOverlayDismissed(true);
    setSaveOverlayOpen(false);
  };

  const handleSaveItinerary = async () => {
    setSaveLoading(true);
    setSaveError("");
    setSaveSuccess("");
    try {
      const lockedSlots = (itinerary?.steps || [])
        .map((step) => step.slot)
        .filter((slot) => Boolean(lockedSteps[slot]));
      const r = await api.post("/itinerary/save", {
        email,
        city_slug: citySlug,
        vibe,
        source_itinerary_id: itinerary?.id,
        steps: itinerary?.steps || [],
        locked_slots: lockedSlots,
      });
      if (r.data?.delivery_status === "sent") {
        setSaveSuccess("Sent — check your email.");
      } else if (r.data?.delivery_status === "provider_unconfigured") {
        setSaveSuccess("Your move is saved. Email sending is not configured yet.");
      } else if (r.data?.delivery_status === "failed") {
        setSaveSuccess("Saved, but the email could not be sent. Try again.");
      } else {
        setSaveSuccess("Your move is saved. Email sending is not configured yet.");
      }
    } catch (e) {
      if (e?.response?.status === 400) {
        setSaveError("Enter a valid email.");
      } else {
        setSaveError("Couldn't save this yet. Try again.");
      }
    } finally {
      setSaveLoading(false);
    }
  };

  const directionsUrl = (b) => {
    const q = encodeURIComponent(b.address || b.name);
    return `https://www.google.com/maps/search/?api=1&query=${q}`;
  };

  const handleAction = (type, b) => {
    trackEvent(type, { business_id: b.id, itinerary_id: itinerary?.id, vibe, city_slug: citySlug });
  };

  return (
    <div
      className="relative min-h-screen bg-black text-white overflow-hidden"
      data-testid="tonight-page"
    >
      {/* Atmospherics */}
      <div className="pointer-events-none absolute inset-0 film-grain opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_55%,_#000_100%)]" />
      <div className="pointer-events-none absolute inset-0 strobe-dim bg-black" />
      <div className="pointer-events-none absolute inset-x-0 h-px bg-white/40 scanline-anim" />

      {/* Corner marks */}
      <div className="absolute top-5 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        YND <span className="lime-dot mx-1.5">/</span> ONE NIGHT ONLY
      </div>
      <div className="absolute top-5 right-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/40 select-none">
        Vol. 003
      </div>

      <button
        onClick={() => navigate(cityPath(citySlug, "vibe"))}
        className="absolute top-14 left-6 z-10 text-[10px] uppercase tracking-[0.3em] text-white/50 hover:text-[#C6FF00] transition-colors"
        data-testid="tonight-back-button"
      >
        ← Back
      </button>

      {/* HEADER */}
      <div className="relative z-10 px-5 sm:px-10 pt-24 pb-8 max-w-3xl mx-auto w-full">
        <div className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-3">
          Curated for {vibeMeta.emoji} {vibeMeta.label}
        </div>
        {sponsorship?.sponsor_name && (
          <div className="mb-4 flex items-center gap-3 text-white/70" data-testid="tonight-sponsorship">
            {sponsorship.sponsor_logo_url ? (
              <img
                src={sponsorship.sponsor_logo_url}
                alt=""
                className="h-8 w-8 rounded-md object-cover border border-white/10"
              />
            ) : null}
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.28em] text-white/40">Sponsored by</div>
              {sponsorship.sponsor_url ? (
                <a
                  href={sponsorship.sponsor_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-display text-sm text-white hover:text-[#C6FF00] transition-colors"
                  data-testid="tonight-sponsorship-link"
                >
                  {sponsorship.sponsor_name}
                </a>
              ) : (
                <div className="font-display text-sm text-white" data-testid="tonight-sponsorship-name">
                  {sponsorship.sponsor_name}
                </div>
              )}
              {sponsorship.tagline ? (
                <div className="text-xs text-white/45" data-testid="tonight-sponsorship-tagline">
                  {sponsorship.tagline}
                </div>
              ) : null}
            </div>
          </div>
        )}
        <motion.h1
          className="font-flyer text-white uppercase"
          style={{
            fontSize: "clamp(2.4rem, 9vw, 7rem)",
            transform: "rotate(-1.5deg)",
            transformOrigin: "left",
            lineHeight: "0.88",
          }}
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.55 }}
          data-testid="tonight-headline"
        >
          Tonight's<br />Move<span className="lime-dot">.</span>
        </motion.h1>
      </div>

      {/* STEPS — simple numbered progression */}
      <div className="relative z-10 px-5 sm:px-10 pb-16 max-w-3xl mx-auto w-full">
        {error ? (
          <div className="border-t border-white/10 py-10 text-white/60" data-testid="tonight-error">
            {error}
            <button
              onClick={() => generate()}
              className="mt-4 block font-flyer uppercase text-[#C6FF00] hover:underline text-sm tracking-[0.2em]"
            >
              Try again →
            </button>
          </div>
        ) : loading && !itinerary ? (
          <div className="space-y-0" data-testid="tonight-loading">
            {[1, 2, 3, 4].map((i) => (
              <div key={`tonight-skel-${i}`} className="border-t border-white/10 py-10">
                <div className="h-12 w-24 bg-white/5 animate-pulse" />
                <div className="mt-4 h-56 w-full bg-white/5 animate-pulse" />
              </div>
            ))}
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={itinerary?.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.4 }}
            >
              {itinerary?.steps?.length === 0 ? (
                <div
                  className="border-t border-white/10 py-10 text-white/60"
                  data-testid="tonight-empty"
                >
                  The catalog's thin. Pick a different vibe.
                </div>
              ) : (
                itinerary.steps.map((step, idx) => (
                  <StepCard
                    key={`${itinerary.id}-${step.slot}`}
                    step={step}
                    idx={idx}
                    total={itinerary.steps.length}
                    locked={Boolean(lockedSteps[step.slot])}
                    onLock={handleLockStep}
                    onUnlock={handleUnlockStep}
                    onAction={handleAction}
                    directionsUrl={directionsUrl}
                  />
                ))
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Another night CTA */}
      {itinerary && itinerary.steps.length > 0 && (
        <motion.div
          className="relative z-10 px-5 sm:px-10 pb-32 max-w-3xl mx-auto w-full border-t border-white/10 pt-10"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <motion.button
            onClick={handleAnother}
            disabled={regenerating}
            className="group font-flyer text-white hover:text-[#C6FF00] disabled:opacity-50 uppercase text-left leading-[0.88] transition-colors"
            style={{ fontSize: "clamp(1.9rem, 7vw, 4.5rem)" }}
            whileTap={{ scale: 0.985 }}
            data-testid="tonight-another-button"
          >
            <span className="inline-flex items-center gap-3 sm:gap-4">
              {regenerating ? (
                <RotateCw className="w-7 h-7 sm:w-10 sm:h-10 animate-spin" />
              ) : (
                <span aria-hidden className="inline-block group-hover:rotate-180 transition-transform duration-500">
                  ↺
                </span>
              )}
              Another night<span className="lime-dot">.</span>
            </span>
          </motion.button>
          <div className="mt-3 text-[10px] uppercase tracking-[0.3em] text-white/40">
            Every night is different
          </div>
        </motion.div>
      )}

      {saveOverlayOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm px-5 sm:px-10"
          data-testid="tonight-save-overlay"
        >
          <div className="min-h-screen flex items-center justify-center">
            <div className="w-full max-w-md border border-white/10 bg-[#070707] p-6 sm:p-8 shadow-[0_0_60px_rgba(198,255,0,0.08)]">
              <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">
                Final move
              </div>
              <h2
                className="mt-3 font-flyer uppercase text-white leading-[0.9]"
                style={{ fontSize: "clamp(2rem, 8vw, 3.75rem)" }}
              >
                You're Locked In
              </h2>
              <p className="mt-4 text-sm text-white/65 leading-relaxed">
                Save and send Tonight&apos;s Move to your email.
              </p>

              {saveSuccess ? (
                <div className="mt-6 border border-[#C6FF00]/25 bg-[#C6FF00]/10 px-4 py-3 text-sm text-white">
                  {saveSuccess}
                </div>
              ) : (
                <>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email address"
                    className="mt-6 w-full border border-white/15 bg-black px-4 py-3 text-sm text-white placeholder:text-white/30 focus:border-[#C6FF00] focus:outline-none"
                    data-testid="tonight-save-email-input"
                  />
                  {saveError ? (
                    <div className="mt-3 text-sm text-[#FF8A8A]" data-testid="tonight-save-error">
                      {saveError}
                    </div>
                  ) : null}
                </>
              )}

              <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={closeSaveOverlay}
                  className="inline-flex items-center justify-center px-4 py-3 border border-white/15 text-white uppercase text-[10px] tracking-[0.22em] font-bold transition-colors hover:border-[#C6FF00] hover:text-[#C6FF00]"
                  data-testid="tonight-save-keep-editing"
                >
                  {saveSuccess ? "Close" : "Keep editing"}
                </button>
                {!saveSuccess ? (
                  <button
                    type="button"
                    onClick={handleSaveItinerary}
                    disabled={saveLoading}
                    className="inline-flex items-center justify-center px-4 py-3 border border-[#C6FF00] bg-[#C6FF00] text-black uppercase text-[10px] tracking-[0.22em] font-bold transition-colors hover:bg-white hover:border-white disabled:opacity-60"
                    data-testid="tonight-save-submit"
                  >
                    {saveLoading ? "Saving..." : "Send Tonight's Move"}
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Marquee */}
      <div className="absolute bottom-0 inset-x-0 z-10 border-t border-white/10 bg-black/80 backdrop-blur-sm overflow-hidden">
        <div className="marquee-track flex whitespace-nowrap py-3 sm:py-4">
          {Array.from({ length: 16 }).map((_, i) => (
            <span
              key={`marquee-${i}`}
              className="font-flyer text-sm sm:text-base px-6 tracking-[0.18em] text-white/70"
            >
              {MARQUEE}
              <span className="lime-dot mx-3">?</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function StepCard({ step, idx, total, locked, onLock, onUnlock, onAction, directionsUrl }) {
  const b = step.business || {};
  const event = step.event;
  const imageUrl = resolveImageUrl(b) || event?.image_url;
  const sponsored = b.sponsor_tier && b.sponsor_tier !== "none";
  const title = SLOT_TITLES[step.slot] || step.label.toUpperCase();
  const number = String(idx + 1).padStart(2, "0");
  const eventTime = formatEventTime(event?.local_time);

  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className={`border-t py-8 sm:py-10 ${
        locked
          ? "border-[#C6FF00]/60 bg-[linear-gradient(180deg,rgba(198,255,0,0.08),rgba(0,0,0,0))]"
          : "border-white/10"
      }`}
      data-testid={`tonight-step-${step.slot}`}
    >
      {/* Top row: number + slot label + featured tag */}
      <div className="flex items-center gap-4 mb-4">
        <div
          className="font-flyer text-[#C6FF00] leading-none tabular-nums"
          style={{ fontSize: "clamp(2.5rem, 7vw, 4.5rem)" }}
        >
          {number}
        </div>
        <div className="flex-1 flex flex-col">
          <div className="text-[10px] uppercase tracking-[0.3em] text-white/40">
            Step {idx + 1} of {total}
          </div>
          <div className="text-[11px] uppercase tracking-[0.3em] text-white mt-1 flex flex-wrap items-center gap-x-2">
            <span>{title}</span>
            {locked && (
              <>
                <span className="text-white/30">·</span>
                <span
                  className="text-[#C6FF00]"
                  data-testid={`tonight-locked-badge-${step.slot}`}
                >
                  Locked in
                </span>
              </>
            )}
            {sponsored && (
              <>
                <span className="text-white/30">·</span>
                <span
                  className="text-[#C6FF00]"
                  data-testid={`tonight-sponsored-badge-${b.id}`}
                >
                  Featured Tonight
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Image — hero */}
      <div className="relative aspect-[16/10] sm:aspect-[2/1] overflow-hidden border border-white/10 bg-[#0A0A0A] mb-5">
        {imageUrl && (
          <img
            src={imageUrl}
            alt={b.name}
            className="w-full h-full object-cover grayscale-[12%] hover:grayscale-0 transition-all duration-700"
            loading="lazy"
          />
        )}
      </div>

      {/* Business name — the actual hero */}
      <h2
        className="font-flyer uppercase text-white leading-[0.9]"
        style={{ fontSize: "clamp(1.8rem, 6vw, 3.75rem)" }}
        data-testid={`tonight-business-name-${b.id}`}
      >
        {b.name}
      </h2>

      {event && (
        <div className="mt-4 border-l-2 border-[#C6FF00] pl-3" data-testid={`tonight-event-${b.id}`}>
          <div className="text-[10px] uppercase tracking-[0.24em] text-[#C6FF00]">
            Tonight: {event.title}
          </div>
          <div className="mt-1 text-xs uppercase tracking-[0.18em] text-white/55">
            {[eventTime, event.venue_name || b.name].filter(Boolean).join(" · ")}
          </div>
        </div>
      )}

      <p className="mt-3 text-white/65 text-sm leading-relaxed max-w-xl">
        {b.description}
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        {locked ? (
          <>
            <button
              type="button"
              className="inline-flex items-center gap-2 px-4 py-3 border border-[#C6FF00] bg-[#C6FF00] text-black uppercase text-[10px] tracking-[0.22em] font-bold"
              data-testid={`tonight-lock-${step.slot}`}
            >
              Locked in
            </button>
            <button
              type="button"
              onClick={() => onUnlock(step.slot)}
              className="inline-flex items-center gap-2 px-4 py-3 border border-white/20 text-white uppercase text-[10px] tracking-[0.22em] font-bold transition-colors hover:border-[#C6FF00] hover:text-[#C6FF00]"
              data-testid={`tonight-unlock-${step.slot}`}
            >
              Unlock
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => onLock(step)}
            className="inline-flex items-center gap-2 px-4 py-3 border border-white/20 text-white uppercase text-[10px] tracking-[0.22em] font-bold transition-colors hover:border-[#C6FF00] hover:text-[#C6FF00]"
            data-testid={`tonight-lock-${step.slot}`}
          >
            Lock this in
          </button>
        )}
        {b.phone ? (
          <ActionBtn
            href={`tel:${b.phone}`}
            onClick={() => onAction("phone_click", b)}
            testid={`tonight-call-${b.id}`}
            icon={<Phone className="w-3.5 h-3.5" />}
          >
            Call
          </ActionBtn>
        ) : null}
        {b.address || b.name ? (
          <ActionBtn
            href={directionsUrl(b)}
            target="_blank"
            onClick={() => onAction("directions_click", b)}
            testid={`tonight-directions-${b.id}`}
            icon={<Navigation className="w-3.5 h-3.5" />}
          >
            Directions
          </ActionBtn>
        ) : null}
        {b.website ? (
          <ActionBtn
            href={b.website}
            target="_blank"
            onClick={() => onAction("website_click", b)}
            testid={`tonight-website-${b.id}`}
            icon={<Globe className="w-3.5 h-3.5" />}
            primary
          >
            Website
          </ActionBtn>
        ) : null}
        {event?.ticket_url ? (
          <ActionBtn
            href={event.ticket_url}
            target="_blank"
            onClick={() => onAction("ticket_click", b)}
            testid={`tonight-tickets-${b.id}`}
            icon={<ExternalLink className="w-3.5 h-3.5" />}
            primary
          >
            Buy Tickets
          </ActionBtn>
        ) : null}
      </div>
    </motion.section>
  );
}

function ActionBtn({ children, href, target, onClick, testid, icon, primary }) {
  return (
    <a
      href={href}
      target={target}
      rel={target ? "noopener noreferrer" : undefined}
      onClick={onClick}
      data-testid={testid}
      className={`inline-flex items-center gap-2 px-4 py-3 border uppercase text-[10px] tracking-[0.22em] font-bold transition-colors active:scale-95 ${
        primary
          ? "bg-[#C6FF00] text-black border-[#C6FF00] hover:bg-white hover:border-white"
          : "border-white/20 text-white hover:border-[#C6FF00] hover:text-[#C6FF00]"
      }`}
    >
      {icon}
      <span>{children}</span>
    </a>
  );
}
