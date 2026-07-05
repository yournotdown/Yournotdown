jest.mock("axios", () => ({
  create: jest.fn(() => ({
    post: jest.fn(),
  })),
}));

import { API, formatEventSchedule, matchedEventsForBusinesses, resolveImageUrl } from "./api";

describe("resolveImageUrl", () => {
  test("prefers uploaded image paths", () => {
    expect(resolveImageUrl({
      image_path: "yourenotdown/images/example.jpg",
      image_url: "https://example.com/image.jpg",
      google_photo_names: ["places/example/photos/reference"],
    })).toBe(`${API}/files/yourenotdown/images/example.jpg`);
  });

  test("prefers explicit image URLs over Google photo names", () => {
    expect(resolveImageUrl({
      image_url: "https://example.com/image.jpg",
      google_photo_names: ["places/example/photos/reference"],
    })).toBe("https://example.com/image.jpg");
  });

  test("falls back to the backend Google Places photo proxy", () => {
    const photoName = "places/ChIJ_example/photos/reference";
    expect(resolveImageUrl({ google_photo_names: [photoName] }))
      .toBe(`${API}/google-places/photo?photo_name=${encodeURIComponent(photoName)}`);
  });

  test("returns an empty string when no image source exists", () => {
    expect(resolveImageUrl({})).toBe("");
  });
});

describe("event helpers", () => {
  test("formats event schedule with date and time", () => {
    expect(formatEventSchedule({ local_date: "2026-07-05", local_time: "19:30:00" }))
      .toBe("2026-07-05 · 19:30:00");
    expect(formatEventSchedule({ local_date: "2026-07-05" })).toBe("2026-07-05");
  });

  test("collects unique matched events from businesses", () => {
    const event = { id: "event-1", title: "Show" };
    expect(
      matchedEventsForBusinesses([
        { id: "business-1", event },
        { id: "business-2", event },
        { id: "business-3" },
      ])
    ).toEqual([event]);
  });
});
