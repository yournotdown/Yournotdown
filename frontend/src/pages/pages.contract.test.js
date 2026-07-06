import fs from "fs";
import path from "path";

const tonightPageSource = fs.readFileSync(path.join(__dirname, "TonightPage.jsx"), "utf8");
const vibePageSource = fs.readFileSync(path.join(__dirname, "VibePage.jsx"), "utf8");

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
