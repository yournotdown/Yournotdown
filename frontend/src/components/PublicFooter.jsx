export default function PublicFooter({ className = "", compact = false }) {
  return (
    <div className={className} data-testid="public-footer-links">
      <div className={`flex flex-wrap items-center gap-x-4 gap-y-2 text-white/40 ${compact ? "text-[10px] uppercase tracking-[0.24em]" : "text-xs"}`}>
        <a href="/terms" className="hover:text-[#C6FF00] transition-colors">Terms</a>
        <a href="/privacy" className="hover:text-[#C6FF00] transition-colors">Privacy</a>
        <a href="/contact" className="hover:text-[#C6FF00] transition-colors">Contact</a>
      </div>
    </div>
  );
}
