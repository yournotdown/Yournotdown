import PublicFooter from "../components/PublicFooter";

const sections = [
  {
    title: "What We Collect",
    body: "We collect emails submitted for saved itineraries, business inquiry contact details, business owner emails used for dashboard access, and basic analytics information such as visitor_id, QR slug attribution, and technical request logs.",
  },
  {
    title: "Saved Itineraries",
    body: "When you save Tonight’s Move, we store the email address you provide along with the itinerary details, selected vibe, optional marketing preference, visitor_id, and any QR attribution tied to that session.",
  },
  {
    title: "Business Inquiries",
    body: "When you submit the public contact form, we store the name, email, business name, phone, inquiry type, and message you provide so we can review the inquiry and follow up if appropriate.",
  },
  {
    title: "Business Owner Access",
    body: "Business owner emails are used for invite links, passwordless dashboard login links, and account access records. We use hashed login and session tokens rather than storing raw access tokens.",
  },
  {
    title: "Analytics and Attribution",
    body: "We use visitor_id-style analytics to understand usage and returning visitors. We also store QR slug attribution when traffic comes from hotel or partner QR placements so we can measure usage and conversions.",
  },
  {
    title: "Email Delivery and Service Providers",
    body: "We use Resend for email delivery where configured, including saved-itinerary emails, business owner access emails, and optional internal contact notifications.",
  },
  {
    title: "What We Do Not Claim",
    body: "We do not sell personal information. We keep public privacy claims conservative and may update this page as our launch operations mature.",
  },
  {
    title: "Questions or Deletion Requests",
    body: "If you have privacy questions or want to request deletion of information you submitted, contact us through the Contact page and include the email address involved.",
  },
];

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#050505] px-6 py-12 text-white" data-testid="privacy-page">
      <div className="mx-auto max-w-3xl">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
        <h1 className="mt-4 font-flyer text-5xl uppercase leading-[0.92]">Privacy</h1>
        <p className="mt-4 text-sm leading-7 text-white/68">
          This Privacy Policy explains how YourNotDown collects, uses, and protects information submitted through the service.
        </p>

        <div className="mt-10 space-y-8">
          {sections.map((section) => (
            <section key={section.title} className="border border-white/10 bg-[#121218] p-6">
              <h2 className="text-[11px] font-black uppercase tracking-[0.22em] text-[#C6FF00]">{section.title}</h2>
              <p className="mt-3 text-sm leading-7 text-white/72">{section.body}</p>
            </section>
          ))}
        </div>

        <PublicFooter className="mt-10 border-t border-white/10 pt-5" />
      </div>
    </div>
  );
}
