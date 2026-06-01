import { motion } from "framer-motion";
import { Clock, ExternalLink, MapPin } from "lucide-react";

export default function EventCard({ event, index }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      className="bg-[#121218] overflow-hidden border border-white/10 shadow-2xl group"
      data-testid={`event-card-${event.id || event.external_event_id}`}
    >
      {event.image_url && (
        <div className="relative w-full h-52 bg-[#1A1A22] overflow-hidden">
          <img
            src={event.image_url}
            alt={event.title}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            loading="lazy"
          />
        </div>
      )}

      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <h3 className="font-display text-xl sm:text-2xl font-bold text-white leading-tight">
            {event.title}
          </h3>
          {event.status && (
            <span className="shrink-0 border border-[#C6FF00]/40 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-[#C6FF00]">
              {event.status}
            </span>
          )}
        </div>

        <div className="mt-4 space-y-2 text-xs uppercase tracking-[0.16em] text-white/55">
          {event.venue_name && (
            <div className="flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-[#C6FF00]" />
              <span>{event.venue_name}</span>
            </div>
          )}
          {event.local_time && (
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-[#C6FF00]" />
              <span>{event.local_time}</span>
            </div>
          )}
        </div>

        {event.ticket_url && (
          <a
            href={event.ticket_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 inline-flex items-center gap-2 bg-[#C6FF00] px-4 py-3 text-[10px] font-bold uppercase tracking-[0.22em] text-black transition-colors hover:bg-white active:scale-95"
            data-testid={`event-tickets-${event.id || event.external_event_id}`}
          >
            Tickets
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>
    </motion.article>
  );
}
