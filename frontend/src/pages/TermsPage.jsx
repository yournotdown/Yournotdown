import PublicFooter from "../components/PublicFooter";

const sections = [
  {
    title: "Recommendations Only",
    body: "YourNotDown provides nightlife and activity recommendations for discovery purposes only. We do not own, operate, manage, or control third-party venues, restaurants, bars, events, hotels, transportation providers, or ticketing platforms.",
  },
  {
    title: "Your Decisions",
    body: "You are responsible for your own decisions, safety, transportation, age eligibility, alcohol consumption, venue rules, allergies, dietary restrictions, purchases, and conduct.",
  },
  {
    title: "Details Can Change",
    body: "Venue hours, pricing, availability, events, admission, lineups, age restrictions, menus, and experiences can change without notice. Verify important details directly with the business before you go.",
  },
  {
    title: "No Guarantees",
    body: "YourNotDown does not guarantee safety, availability, quality, legality, admission, pricing, suitability, or any specific outcome. Recommendations are not an instruction to engage in risky, illegal, unsafe, intoxicated, or dangerous behavior.",
  },
  {
    title: "Third-Party Links",
    body: "Links to third-party websites, maps, ticketing pages, and business websites are provided for convenience only. Those websites and services are not controlled by YourNotDown.",
  },
  {
    title: "Sponsored Placements",
    body: "Sponsored or boosted placements may appear in the product. Where sponsorship applies, it should be labeled in the relevant surface.",
  },
  {
    title: "Emergency Situations",
    body: "If you are in danger or need emergency help, call 911 or your local emergency services immediately.",
  },
  {
    title: "Limitation of Liability",
    body: "To the fullest extent permitted by law, YourNotDown and its operators are not liable for losses, injuries, damages, claims, or outcomes arising from your use of the service, third-party businesses, or third-party links.",
  },
];

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#050505] px-6 py-12 text-white" data-testid="terms-page">
      <div className="mx-auto max-w-3xl">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#C6FF00]">YND / EST. 26</div>
        <h1 className="mt-4 font-flyer text-5xl uppercase leading-[0.92]">Terms</h1>
        <p className="mt-4 text-sm leading-7 text-white/68">
          These launch-ready terms are plain-language product terms for YourNotDown. They are not a promise of complete legal protection and may be updated after attorney review.
        </p>

        <div className="mt-10 space-y-8">
          {sections.map((section) => (
            <section key={section.title} className="border border-white/10 bg-[#121218] p-6">
              <h2 className="text-[11px] font-black uppercase tracking-[0.22em] text-[#C6FF00]">{section.title}</h2>
              <p className="mt-3 text-sm leading-7 text-white/72">{section.body}</p>
            </section>
          ))}
        </div>

        <div className="mt-10 text-sm leading-7 text-white/62">
          Questions about these terms can be sent through <a href="/contact" className="text-white hover:text-[#C6FF00]">our contact page</a>.
        </div>

        <PublicFooter className="mt-10 border-t border-white/10 pt-5" />
      </div>
    </div>
  );
}
