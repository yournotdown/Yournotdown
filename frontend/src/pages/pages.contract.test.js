import fs from "fs";
import path from "path";

const tonightPageSource = fs.readFileSync(path.join(__dirname, "TonightPage.jsx"), "utf8");
const vibePageSource = fs.readFileSync(path.join(__dirname, "VibePage.jsx"), "utf8");
const adminDashboardSource = fs.readFileSync(path.join(__dirname, "AdminDashboardPage.jsx"), "utf8");
const businessClaimSource = fs.readFileSync(path.join(__dirname, "BusinessClaimPage.jsx"), "utf8");
const businessDashboardSource = fs.readFileSync(path.join(__dirname, "BusinessDashboardPage.jsx"), "utf8");
const appSource = fs.readFileSync(path.join(__dirname, "..", "App.js"), "utf8");
const indexHtmlSource = fs.readFileSync(path.join(__dirname, "..", "..", "public", "index.html"), "utf8");
const visitorHelperSource = fs.readFileSync(path.join(__dirname, "..", "lib", "visitor.js"), "utf8");
const qrHelperSource = fs.readFileSync(path.join(__dirname, "..", "lib", "qr.js"), "utf8");

describe("TonightPage source contract", () => {
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

  test("audience panel defends against missing data and exposes a clean error state", () => {
    expect(adminDashboardSource).toContain("const [audienceError, setAudienceError] = useState(\"\")");
    expect(adminDashboardSource).toContain("totals: response?.data?.totals || {}");
    expect(adminDashboardSource).toContain("rows: Array.isArray(response?.data?.rows) ? response.data.rows : []");
    expect(adminDashboardSource).toContain("const rows = Array.isArray(audience?.rows) ? audience.rows : []");
    expect(adminDashboardSource).toContain('data-testid="admin-audience-error"');
    expect(adminDashboardSource).toContain("Couldn’t load audience right now.");
  });
});

describe("Business owner routes source contract", () => {
  test("claim and dashboard routes exist", () => {
    expect(appSource).toContain('path="/business/claim/:token"');
    expect(appSource).toContain('path="/business/dashboard"');
  });

  test("claim page posts token to the business claim endpoint", () => {
    expect(businessClaimSource).toContain('.post("/business/claim", { token })');
    expect(businessClaimSource).toContain('api.get("/business/me")');
    expect(businessClaimSource).toContain('window.location.replace("/business/dashboard")');
    expect(businessClaimSource).toContain("Create Account");
    expect(businessClaimSource).not.toContain("MVP");
  });

  test("dashboard shell contains business and sponsor language", () => {
    expect(businessDashboardSource).toContain('api.get("/business/me")');
    expect(businessDashboardSource).toContain('api.get("/business/analytics")');
    expect(businessDashboardSource).toContain("Business Portal");
    expect(businessDashboardSource).toContain("Sponsor tier:");
    expect(businessDashboardSource).not.toContain("MVP");
    expect(businessDashboardSource).not.toContain("being prepared");
  });

  test("admin revoke action is immediate and clears the local owner email field", () => {
    expect(adminDashboardSource).toContain('.post(`/admin/businesses/${editing.id}/owner-access/revoke`)');
    expect(adminDashboardSource).toContain("await loadOwnerAccess(editing.id, \"\")");
    expect(adminDashboardSource).toContain('setOwnerInviteEmail("")');
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
    const homePageSource = fs.readFileSync(path.join(__dirname, "HomePage.jsx"), "utf8");
    expect(homePageSource).toContain("rememberQrSlugFromSearch(location.search)");
    expect(homePageSource).toContain('trackEvent("hotel_qr_scan", { city_slug: citySlug, qr_slug: qrSlug })');
  });

  test("homepage qr links remain on the root url before redirecting into Nashville", () => {
    const serverSource = fs.readFileSync(path.join(__dirname, "..", "..", "..", "backend", "server.py"), "utf8");
    expect(serverSource).toContain('return f"{base}?qr={qr_slug}"');
  });
});
