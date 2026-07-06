import fs from "fs";
import path from "path";

const tonightPageSource = fs.readFileSync(path.join(__dirname, "TonightPage.jsx"), "utf8");
const vibePageSource = fs.readFileSync(path.join(__dirname, "VibePage.jsx"), "utf8");
const adminDashboardSource = fs.readFileSync(path.join(__dirname, "AdminDashboardPage.jsx"), "utf8");
const businessClaimSource = fs.readFileSync(path.join(__dirname, "BusinessClaimPage.jsx"), "utf8");
const businessDashboardSource = fs.readFileSync(path.join(__dirname, "BusinessDashboardPage.jsx"), "utf8");
const appSource = fs.readFileSync(path.join(__dirname, "..", "App.js"), "utf8");

describe("TonightPage source contract", () => {
  test("Another Night scrolls to the top after a successful reroll", () => {
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
});

describe("VibePage source contract", () => {
  test("still renders all four vibe options", () => {
    expect(vibePageSource).toContain('{ slug: "just-vibing", emoji: "😇", label: "Take It Easy" }');
    expect(vibePageSource).toContain('{ slug: "down", emoji: "😏", label: "Let\'s See Where This Goes" }');
    expect(vibePageSource).toContain('{ slug: "very-down", emoji: "🔥", label: "Let\'s Make It Count" }');
    expect(vibePageSource).toContain('{ slug: "send-it", emoji: "🚀", label: "No Regrets" }');
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
  });

  test("dashboard shell contains business and sponsor language", () => {
    expect(businessDashboardSource).toContain('api.get("/business/me")');
    expect(businessDashboardSource).toContain('api.get("/business/analytics")');
    expect(businessDashboardSource).toContain("Business Portal");
    expect(businessDashboardSource).toContain("Sponsor tier:");
    expect(businessDashboardSource).not.toContain("MVP");
    expect(businessDashboardSource).not.toContain("being prepared");
  });
});
