import fs from "fs";
import path from "path";

const tonightPageSource = fs.readFileSync(path.join(__dirname, "TonightPage.jsx"), "utf8");
const homePageSource = fs.readFileSync(path.join(__dirname, "HomePage.jsx"), "utf8");
const vibePageSource = fs.readFileSync(path.join(__dirname, "VibePage.jsx"), "utf8");
const adminDashboardSource = fs.readFileSync(path.join(__dirname, "AdminDashboardPage.jsx"), "utf8");
const eventCardSource = fs.readFileSync(path.join(__dirname, "..", "components", "EventCard.jsx"), "utf8");
const businessClaimSource = fs.readFileSync(path.join(__dirname, "BusinessClaimPage.jsx"), "utf8");
const businessDashboardSource = fs.readFileSync(path.join(__dirname, "BusinessDashboardPage.jsx"), "utf8");
const businessLoginSource = fs.readFileSync(path.join(__dirname, "BusinessLoginPage.jsx"), "utf8");
const contactPageSource = fs.readFileSync(path.join(__dirname, "ContactPage.jsx"), "utf8");
const termsPageSource = fs.readFileSync(path.join(__dirname, "TermsPage.jsx"), "utf8");
const privacyPageSource = fs.readFileSync(path.join(__dirname, "PrivacyPage.jsx"), "utf8");
const publicFooterSource = fs.readFileSync(path.join(__dirname, "..", "components", "PublicFooter.jsx"), "utf8");
const appSource = fs.readFileSync(path.join(__dirname, "..", "App.js"), "utf8");
const indexHtmlSource = fs.readFileSync(path.join(__dirname, "..", "..", "public", "index.html"), "utf8");
const visitorHelperSource = fs.readFileSync(path.join(__dirname, "..", "lib", "visitor.js"), "utf8");
const qrHelperSource = fs.readFileSync(path.join(__dirname, "..", "lib", "qr.js"), "utf8");

describe("TonightPage source contract", () => {
  test("public shell does not render the old scanline bar", () => {
    expect(homePageSource).not.toContain("scanline-anim");
    expect(vibePageSource).not.toContain("scanline-anim");
    expect(tonightPageSource).not.toContain("scanline-anim");
  });

  test("Run It Back scrolls to the top after a successful reroll", () => {
    expect(tonightPageSource).toContain("scrollToTopOnSuccess = false");
    expect(tonightPageSource).toContain("scrollToTopOnSuccess: true");
    expect(tonightPageSource).toContain('window.scrollTo({ top: 0, behavior: "smooth" })');
    expect(tonightPageSource).toContain("window.requestAnimationFrame(() => {");
  });

  test("lock and ticket actions include sponsor-grade analytics fields", () => {
    expect(tonightPageSource).toContain('trackEvent("step_locked", {');
    expect(tonightPageSource).toContain('source_surface: "tonight_page"');
    expect(tonightPageSource).toContain("slot: step?.slot");
    expect(tonightPageSource).toContain("category_slug: b.category_slug");
    expect(tonightPageSource).toContain('onAction("ticket_click", b, step, {');
    expect(tonightPageSource).toContain("event_id: event.external_event_id || event.id");
    expect(tonightPageSource).toContain("event_source: event.source");
  });

  test("save overlay includes optional marketing opt-in and sends it in the request", () => {
    expect(tonightPageSource).toContain("Send me occasional Nashville picks and YourNotDown updates.");
    expect(tonightPageSource).toContain("We&apos;ll send your saved move either way. Updates are optional.");
    expect(tonightPageSource).toContain("marketing_opt_in: marketingOptIn");
    expect(tonightPageSource).toContain("visitor_id: getVisitorId()");
    expect(tonightPageSource).toContain("qr_slug: getCurrentQrSlug()");
    expect(tonightPageSource).not.toContain("First name");
    expect(tonightPageSource).not.toContain("Last name");
  });

  test("headline keeps sponsorship near MOVE instead of above the title", () => {
    expect(tonightPageSource).toContain('<span className="block">Tonight\'s</span>');
    expect(tonightPageSource).toContain('mt-2 flex flex-col items-start gap-3 sm:flex-row sm:items-end sm:gap-4');
    expect(tonightPageSource).toContain('data-testid="tonight-sponsorship"');
    expect(tonightPageSource).toContain("Sponsored by");
    expect(tonightPageSource).toContain("rounded-full border border-[#C6FF00]/20");
  });

  test("tonight images request narrower google photos and lazy-load card media", () => {
    expect(tonightPageSource).toContain('resolveImageUrl(b, { maxWidth: 960 })');
    expect(tonightPageSource).toContain('loading="lazy"');
    expect(tonightPageSource).toContain('decoding="async"');
    expect(tonightPageSource).toContain('sizes="(min-width: 1024px) 960px, 100vw"');
  });
});

describe("VibePage source contract", () => {
  test("still renders all four vibe options", () => {
    expect(vibePageSource).toContain('{ slug: "just-vibing", emoji: "😇", label: "Take It Easy" }');
    expect(vibePageSource).toContain('{ slug: "down", emoji: "😏", label: "See Where It Goes" }');
    expect(vibePageSource).toContain('{ slug: "very-down", emoji: "🔥", label: "Make It Count" }');
    expect(vibePageSource).toContain('{ slug: "send-it", emoji: "🚀", label: "No Regrets" }');
    expect(vibePageSource).not.toContain("Let's See Where This Goes");
    expect(vibePageSource).not.toContain("Let's Make It Count");
  });

  test("keeps internal vibe slugs and tonight route behavior unchanged", () => {
    expect(vibePageSource).toContain('slug: "just-vibing"');
    expect(vibePageSource).toContain('slug: "down"');
    expect(vibePageSource).toContain('slug: "very-down"');
    expect(vibePageSource).toContain('slug: "send-it"');
    expect(vibePageSource).toContain('navigate(`${cityPath(citySlug, "tonight")}?vibe=${vibe.slug}`)');
    expect(tonightPageSource).toContain('const vibe = searchParams.get("vibe") || "down";');
  });

  test("uses compact desktop grid sizing", () => {
    expect(vibePageSource).toContain("lg:aspect-[9/5]");
    expect(vibePageSource).toContain("lg:max-h-[210px]");
    expect(vibePageSource).toContain("lg:gap-x-4 lg:gap-y-4");
    expect(vibePageSource).toContain("lg:pt-16 lg:pb-20");
  });
});

describe("HomePage source contract", () => {
  test("public homepage does not expose the admin shortcut link", () => {
    expect(homePageSource).not.toContain("homepage-admin-link");
    expect(homePageSource).not.toContain('navigate("/admin/login")');
  });
});

describe("AdminDashboardPage source contract", () => {
  test("admin analytics surfaces sponsor-grade leaderboard labels", () => {
    expect(adminDashboardSource).toContain("Locked In");
    expect(adminDashboardSource).toContain("Saved in Final Move");
    expect(adminDashboardSource).toContain("Buy Tickets");
    expect(adminDashboardSource).toContain("Sponsor Performance");
    expect(adminDashboardSource).toContain("Dinner");
    expect(adminDashboardSource).toContain("Drinks");
    expect(adminDashboardSource).toContain("Late Night");
  });

  test("admin business area includes Invite Owner UI", () => {
    expect(adminDashboardSource).toContain("Business Owner Access");
    expect(adminDashboardSource).toContain("Invite Owner");
    expect(adminDashboardSource).toContain("business-owner-invite-send");
    expect(adminDashboardSource).toContain("business-owner-revoke-access");
    expect(adminDashboardSource).toContain("const loadOwnerAccess = useCallback");
  });

  test("admin dashboard contains audience labels", () => {
    expect(adminDashboardSource).toContain("Audience");
    expect(adminDashboardSource).toContain("Email captures from Save Tonight&apos;s Move.");
    expect(adminDashboardSource).toContain("Email Captures");
    expect(adminDashboardSource).toContain("Marketing Opt-ins");
    expect(adminDashboardSource).toContain("Saved Moves");
    expect(adminDashboardSource).toContain("Returning Visitor Rate");
    expect(adminDashboardSource).toContain("Repeat Savers");
    expect(adminDashboardSource).toContain("returning visitors from stored visitor IDs.");
    expect(adminDashboardSource).toContain("Search by email");
    expect(adminDashboardSource).toContain("Previous");
    expect(adminDashboardSource).toContain("Next");
  });

  test("admin dashboard contains Hotel QR tab and create form labels", () => {
    expect(adminDashboardSource).toContain('{ id: "hotel-qr", label: "Hotel QR", icon: Building2 }');
    expect(adminDashboardSource).toContain("Hotel QR");
    expect(adminDashboardSource).toContain("Create Hotel QR");
    expect(adminDashboardSource).toContain("Hotel name");
    expect(adminDashboardSource).toContain("Location label");
    expect(adminDashboardSource).toContain('data-testid="hotel-qr-form-name"');
    expect(adminDashboardSource).toContain("Copy URL");
    expect(adminDashboardSource).toContain("Download QR");
    expect(adminDashboardSource).toContain("Delete");
    expect(adminDashboardSource).toContain("HotelQrCodePreview");
    expect(adminDashboardSource).toContain("QRCode.toDataURL");
  });

  test("hotel qr delete uses confirmation and calls the delete endpoint", () => {
    expect(adminDashboardSource).toContain("Delete this Hotel QR? This removes it from the admin list but does not delete historical analytics events.");
    expect(adminDashboardSource).toContain('.delete(`/admin/hotel-qr/${qrId}`)');
    expect(adminDashboardSource).toContain("await loadHotelQr()");
    expect(adminDashboardSource).toContain('data-testid={`hotel-qr-delete-${row.slug}`}');
  });

  test("admin business imagery uses lighter previews and lazy loading", () => {
    expect(adminDashboardSource).toContain('resolveImageUrl(form, { maxWidth: 640 })');
    expect(adminDashboardSource).toContain('resolveImageUrl(b, { maxWidth: 240 })');
    expect(adminDashboardSource).toContain('sizes="48px"');
    expect(adminDashboardSource).toContain('decoding="async"');
  });

  test("audience panel defends against missing data and exposes a clean error state", () => {
    expect(adminDashboardSource).toContain("const [audienceError, setAudienceError] = useState(\"\")");
    expect(adminDashboardSource).toContain("totals: response?.data?.totals || {}");
    expect(adminDashboardSource).toContain("rows: Array.isArray(response?.data?.rows) ? response.data.rows : []");
    expect(adminDashboardSource).toContain("meta: response?.data?.meta || {}");
    expect(adminDashboardSource).toContain("const rows = Array.isArray(audience?.rows) ? audience.rows : []");
    expect(adminDashboardSource).toContain("const meta = audience?.meta || {}");
    expect(adminDashboardSource).toContain('data-testid="admin-audience-error"');
    expect(adminDashboardSource).toContain("Couldn’t load audience right now.");
    expect(adminDashboardSource).toContain('data-testid="admin-audience-prev"');
    expect(adminDashboardSource).toContain('data-testid="admin-audience-next"');
  });

  test("admin dashboard contains contact inquiry section", () => {
    expect(adminDashboardSource).toContain('{ id: "contact", label: "Contact", icon: Mail }');
    expect(adminDashboardSource).toContain("Contact Inquiries");
    expect(adminDashboardSource).toContain("admin-contact-panel");
    expect(adminDashboardSource).toContain('api.get("/admin/contact-inquiries"');
    expect(adminDashboardSource).toContain('api.patch(`/admin/contact-inquiries/${inquiryId}`');
    expect(adminDashboardSource).toContain("Mark contacted");
    expect(adminDashboardSource).toContain("Archive");
  });

  test("featured live music copy explains active priority behavior without override wording", () => {
    expect(adminDashboardSource).toContain("The top active same-day featured event is used as the Live Music step while active.");
    expect(adminDashboardSource).toContain("1 appears first in Live Music and is used as the Live Music step while active.");
    expect(adminDashboardSource).toContain("Active featured event");
  });

  test("featured live music form supports both image upload and image url fallback", () => {
    expect(adminDashboardSource).toContain('data-testid="featured-live-music-upload-button"');
    expect(adminDashboardSource).toContain('data-testid="featured-live-music-upload-input"');
    expect(adminDashboardSource).toContain('data-testid="featured-live-music-clear-upload"');
    expect(adminDashboardSource).toContain("Uploaded image is currently being used.");
    expect(adminDashboardSource).toContain("If you upload an image, it will be used before the image URL.");
    expect(adminDashboardSource).toContain("Featured event image uploaded");
    expect(adminDashboardSource).toContain("The top active same-day featured event is used as the Live Music step while active.");
    expect(adminDashboardSource).toContain("1 appears first in Live Music and is used as the Live Music step while active.");
    expect(adminDashboardSource).toContain("Active featured event");
    expect(adminDashboardSource).toContain("This does not require an active sponsorship.");
    expect(adminDashboardSource).toContain("Sponsorship does not control Featured Live Music visibility.");
  });
});

describe("Legal and contact routes source contract", () => {
  test("terms, privacy, and contact routes exist", () => {
    expect(appSource).toContain('path="/terms"');
    expect(appSource).toContain('path="/privacy"');
    expect(appSource).toContain('path="/contact"');
  });

  test("contact page includes business inquiry fields without password or signup copy", () => {
    expect(contactPageSource).toContain("Work With YourNotDown");
    expect(contactPageSource).toContain("For sponsorships, hotel QR placements, venue listings, and business inquiries.");
    expect(contactPageSource).toContain('data-testid="contact-name"');
    expect(contactPageSource).toContain('data-testid="contact-email"');
    expect(contactPageSource).toContain('data-testid="contact-business-name"');
    expect(contactPageSource).toContain('data-testid="contact-phone"');
    expect(contactPageSource).toContain('data-testid="contact-inquiry-type"');
    expect(contactPageSource).toContain('data-testid="contact-message"');
    expect(contactPageSource).toContain('data-testid="contact-honeypot"');
    expect(contactPageSource).toContain('api.post("/contact/inquiries", form)');
    expect(contactPageSource).toContain("Got it. We’ll review your inquiry and get back to you if it’s a fit.");
    expect(contactPageSource).not.toContain("password");
    expect(contactPageSource).not.toContain("sign up");
    expect(contactPageSource).not.toContain("MVP");
  });

  test("terms and privacy pages contain launch-safe legal copy", () => {
    expect(termsPageSource).toContain("YourNotDown provides nightlife and activity recommendations for discovery purposes only.");
    expect(termsPageSource).toContain("call 911 or your local emergency services immediately");
    expect(termsPageSource).toContain("To the fullest extent permitted by law");
    expect(privacyPageSource).toContain("We do not sell personal information.");
    expect(privacyPageSource).toContain("visitor_id-style analytics");
    expect(privacyPageSource).toContain("QR slug attribution");
    expect(privacyPageSource).toContain("Resend for email delivery");
  });

  test("public footer exposes legal and contact links", () => {
    expect(publicFooterSource).toContain('href="/terms"');
    expect(publicFooterSource).toContain('href="/privacy"');
    expect(publicFooterSource).toContain('href="/contact"');
    expect(homePageSource).toContain("PublicFooter");
    expect(vibePageSource).toContain("PublicFooter");
    expect(tonightPageSource).toContain("PublicFooter");
  });
});

describe("Business owner routes source contract", () => {
  test("claim, login, and dashboard routes exist", () => {
    expect(appSource).toContain('path="/business/claim/:token"');
    expect(appSource).toContain('path="/business/login"');
    expect(appSource).toContain('path="/business/dashboard"');
  });

  test("claim page posts token to the business claim endpoint", () => {
    expect(businessClaimSource).toContain('.post("/business/claim", { token })');
    expect(businessClaimSource).toContain('api.get("/business/me")');
    expect(businessClaimSource).toContain('window.location.replace("/business/dashboard")');
    expect(businessClaimSource).toContain("Activate Dashboard Access");
    expect(businessClaimSource).not.toContain("MVP");
  });

  test("login page requests and claims owner magic links without a password field", () => {
    expect(businessLoginSource).toContain('.post("/business/login-request", { email })');
    expect(businessLoginSource).toContain('.post("/business/login-claim", { token })');
    expect(businessLoginSource).toContain('window.location.replace("/business/dashboard")');
    expect(businessLoginSource).toContain("Access your business dashboard");
    expect(businessLoginSource).toContain("Send Magic Link");
    expect(businessLoginSource).toContain("type=\"email\"");
    expect(businessLoginSource).not.toContain("type=\"password\"");
    expect(businessLoginSource).not.toContain("Create account");
    expect(businessLoginSource).not.toContain("MVP");
  });

  test("dashboard shell contains business and sponsor language", () => {
    expect(businessDashboardSource).toContain('api.get("/business/me")');
    expect(businessDashboardSource).toContain('api.get("/business/analytics")');
    expect(businessDashboardSource).toContain("Business Portal");
    expect(businessDashboardSource).toContain("Sponsor tier:");
    expect(businessDashboardSource).toContain("Your dashboard access is active.");
    expect(businessDashboardSource).toContain("yournotdown.com/business/login");
    expect(businessDashboardSource).toContain("Return login page");
    expect(businessDashboardSource).toContain("Need help?");
    expect(businessDashboardSource).toContain("Your session expired. Request a fresh secure login link.");
    expect(businessDashboardSource).toContain("Send me a login link");
    expect(businessDashboardSource).toContain('data-testid="business-dashboard-email"');
    expect(businessDashboardSource).toContain('href="/business/login"');
    expect(businessDashboardSource).not.toContain("MVP");
    expect(businessDashboardSource).not.toContain("being prepared");
  });

  test("admin revoke action is immediate and clears the local owner email field", () => {
    expect(adminDashboardSource).toContain('.post(`/admin/businesses/${editing.id}/owner-access/revoke`)');
    expect(adminDashboardSource).toContain("await loadOwnerAccess(editing.id, \"\")");
    expect(adminDashboardSource).toContain('setOwnerInviteEmail("")');
  });
});

describe("Featured live music public rendering contract", () => {
  test("event cards can render uploaded featured-event images", () => {
    expect(eventCardSource).toContain("resolveImageUrl(event, { maxWidth: 960 })");
    expect(eventCardSource).toContain("const imageUrl = resolveImageUrl(event, { maxWidth: 960 });");
    expect(eventCardSource).toContain("src={imageUrl}");
  });
});

describe("Brand assets contract", () => {
  test("index.html prefers the local YND SVG favicon", () => {
    expect(indexHtmlSource).toContain('rel="icon" type="image/svg+xml" href="%PUBLIC_URL%/favicon.svg"');
    expect(indexHtmlSource).toContain('rel="alternate icon" href="%PUBLIC_URL%/favicon.svg"');
  });
});

describe("Visitor tracking contract", () => {
  test("visitor helper stores a local visitor id", () => {
    expect(visitorHelperSource).toContain('const VISITOR_ID_KEY = "ynd_visitor_id"');
    expect(visitorHelperSource).toContain("window.localStorage.getItem(VISITOR_ID_KEY)");
    expect(visitorHelperSource).toContain("window.localStorage.setItem(VISITOR_ID_KEY, nextId)");
  });

  test("api analytics tracking includes visitor ids", () => {
    const apiSource = fs.readFileSync(path.join(__dirname, "..", "lib", "api.js"), "utf8");
    expect(apiSource).toContain('visitor_id: getVisitorId()');
    expect(apiSource).toContain('qr_slug: getCurrentQrSlug()');
  });

  test("qr helper detects qr params and persists them", () => {
    expect(qrHelperSource).toContain('const QR_SLUG_KEY = "ynd_qr_slug"');
    expect(qrHelperSource).toContain("new URLSearchParams(search || \"\")");
    expect(qrHelperSource).toContain("params.get(\"qr\")");
    expect(qrHelperSource).toContain("window.localStorage?.setItem(QR_SLUG_KEY, qrSlug)");
    expect(qrHelperSource).toContain('window.sessionStorage?.setItem(seenKey, "1")');
  });

  test("homepage stores qr slug and fires the hotel qr scan event", () => {
    expect(homePageSource).toContain("rememberQrSlugFromSearch(location.search)");
    expect(homePageSource).toContain('trackEvent("hotel_qr_scan", { city_slug: citySlug, qr_slug: qrSlug })');
  });

  test("homepage qr links remain on the root url before redirecting into Nashville", () => {
    const serverSource = fs.readFileSync(path.join(__dirname, "..", "..", "..", "backend", "server.py"), "utf8");
    expect(serverSource).toContain('return f"{base}?qr={qr_slug}"');
  });

  test("google photo proxy supports bounded widths and longer cache headers", () => {
    const serverSource = fs.readFileSync(path.join(__dirname, "..", "..", "..", "backend", "server.py"), "utf8");
    const googlePhotoSource = fs.readFileSync(path.join(__dirname, "..", "..", "..", "backend", "google_places_photos.py"), "utf8");
    expect(serverSource).toContain("max_width: Optional[int] = None");
    expect(serverSource).toContain("safe_max_width = normalize_google_places_photo_width(max_width)");
    expect(serverSource).toContain('"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"');
    expect(googlePhotoSource).toContain("normalize_google_places_photo_width");
    expect(googlePhotoSource).toContain('params={"maxWidthPx": normalize_google_places_photo_width(max_width_px), "key": api_key}');
  });
});
