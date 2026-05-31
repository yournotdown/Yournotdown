import {
  DEFAULT_CITY_SLUG,
  activeCitySlug,
  cityDisplayName,
  cityPath,
} from "./cities";

describe("city routing helpers", () => {
  test("defaults to Nashville", () => {
    expect(DEFAULT_CITY_SLUG).toBe("nashville");
    expect(activeCitySlug()).toBe("nashville");
    expect(cityPath()).toBe("/nashville");
  });

  test("builds city-prefixed paths", () => {
    expect(cityPath("miami", "vibe")).toBe("/miami/vibe");
    expect(cityPath("atlanta", "/tonight")).toBe("/atlanta/tonight");
  });

  test("formats city slugs for display", () => {
    expect(cityDisplayName("nashville")).toBe("Nashville");
    expect(cityDisplayName("fort-lauderdale")).toBe("Fort Lauderdale");
  });
});
