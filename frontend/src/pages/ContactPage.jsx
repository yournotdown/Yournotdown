import { useState } from "react";
import { api } from "../lib/api";
import PublicFooter from "../components/PublicFooter";

const EMPTY_FORM = {
  name: "",
  email: "",
  business_name: "",
  phone: "",
  inquiry_type: "Sponsor inquiry",
  message: "",
  website: "",
};

export default function ContactPage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const response = await api.post("/contact/inquiries", form);
      setSuccess(response?.data?.message || "Got it. We’ll review your inquiry and get back to you if it’s a fit.");
      setForm(EMPTY_FORM);
    } catch (err) {
      setError(err?.response?.data?.detail || "We couldn’t send that right now. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] px-6 py-12 text-white" data-testid="contact-page">
      <div className="mx-auto max-w-3xl">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
        <h1 className="mt-4 font-flyer text-5xl uppercase leading-[0.92]">Work With YourNotDown</h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-white/68">
          For sponsorships, hotel QR placements, venue listings, and business inquiries.
        </p>

        <form onSubmit={handleSubmit} className="mt-10 grid gap-5 border border-white/10 bg-[#121218] p-6 sm:grid-cols-2" data-testid="contact-form">
          <div>
            <label className="text-[10px] uppercase tracking-[0.24em] text-white/45">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(event) => handleChange("name", event.target.value)}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              data-testid="contact-name"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.24em] text-white/45">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(event) => handleChange("email", event.target.value)}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              data-testid="contact-email"
              required
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.24em] text-white/45">Business name</label>
            <input
              type="text"
              value={form.business_name}
              onChange={(event) => handleChange("business_name", event.target.value)}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              data-testid="contact-business-name"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.24em] text-white/45">Phone (optional)</label>
            <input
              type="text"
              value={form.phone}
              onChange={(event) => handleChange("phone", event.target.value)}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              data-testid="contact-phone"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-[10px] uppercase tracking-[0.24em] text-white/45">Inquiry type</label>
            <select
              value={form.inquiry_type}
              onChange={(event) => handleChange("inquiry_type", event.target.value)}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              data-testid="contact-inquiry-type"
            >
              <option>Sponsor inquiry</option>
              <option>Hotel QR placement</option>
              <option>Venue listing</option>
              <option>Restaurant/bar partnership</option>
              <option>Press/media</option>
              <option>General</option>
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="text-[10px] uppercase tracking-[0.24em] text-white/45">Message</label>
            <textarea
              value={form.message}
              onChange={(event) => handleChange("message", event.target.value)}
              rows={7}
              className="mt-2 w-full border border-white/10 bg-[#050505] px-4 py-3 text-sm text-white outline-none focus:border-[#C6FF00]"
              data-testid="contact-message"
              required
            />
          </div>
          <div className="hidden">
            <label htmlFor="contact-website">Website</label>
            <input
              id="contact-website"
              type="text"
              value={form.website}
              onChange={(event) => handleChange("website", event.target.value)}
              tabIndex="-1"
              autoComplete="off"
              data-testid="contact-honeypot"
            />
          </div>
          {success ? (
            <div className="sm:col-span-2 border border-[#C6FF00]/20 bg-[#C6FF00]/10 px-4 py-3 text-sm text-white" data-testid="contact-success">
              {success}
            </div>
          ) : null}
          {error ? (
            <div className="sm:col-span-2 border border-red-400/20 bg-red-500/[0.08] px-4 py-3 text-sm text-red-100" data-testid="contact-error">
              {error}
            </div>
          ) : null}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center justify-center border border-[#C6FF00] bg-[#C6FF00] px-5 py-3 text-[11px] font-black uppercase tracking-[0.22em] text-black disabled:opacity-60"
              data-testid="contact-submit"
            >
              {saving ? "Sending..." : "Send Inquiry"}
            </button>
          </div>
        </form>

        <PublicFooter className="mt-10 border-t border-white/10 pt-5" />
      </div>
    </div>
  );
}
