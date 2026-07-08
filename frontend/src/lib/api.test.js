jest.mock("axios", () => ({
  ...(() => {
    const mockPost = jest.fn(() => Promise.resolve({ data: { ok: true } }));
    return {
      __mockPost: mockPost,
      create: jest.fn(() => ({
        post: mockPost,
      })),
    };
  })(),
}));

import { API, formatEventSchedule, formatEventTime, matchedEventsForBusinesses, resolveImageUrl, trackEvent } from "./api";

const getPostMock = () => {
  const axios = require("axios");
  return axios.__mockPost;
};

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

  test("supports narrower google photo widths for card and admin thumbnails", () => {
    const photoName = "places/ChIJ_example/photos/reference";
    expect(resolveImageUrl({ google_photo_names: [photoName] }, { maxWidth: 320 }))
      .toBe(`${API}/google-places/photo?photo_name=${encodeURIComponent(photoName)}&max_width=320`);
  });

  test("returns an empty string when no image source exists", () => {
    expect(resolveImageUrl({})).toBe("");
  });
});

describe("event helpers", () => {
  beforeEach(() => {
    getPostMock().mockClear();
    window.localStorage.clear();
    window.sessionStorage.clear();
    Object.defineProperty(window, "crypto", {
      value: {
        randomUUID: jest.fn(() => "visitor-123"),
      },
      configurable: true,
    });
  });

  test("formats event schedule with date and time", () => {
    expect(formatEventSchedule({ local_date: "2026-07-05", local_time: "19:30:00" }))
      .toBe("2026-07-05 · 19:30:00");
    expect(formatEventSchedule({ local_date: "2026-07-05" })).toBe("2026-07-05");
  });

  test("formats event time for Tonight step cards", () => {
    expect(formatEventTime("18:05:00")).toBe("6:05 PM");
    expect(formatEventTime("00:15:00")).toBe("12:15 AM");
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

  test("analytics tracking includes visitor_id and qr_slug when present", async () => {
    window.localStorage.setItem("ynd_qr_slug", "russell-lobby");
    trackEvent("homepage_visit", { city_slug: "nashville" });
    await Promise.resolve();
    expect(getPostMock()).toHaveBeenCalledWith("/analytics/track", {
      event_type: "homepage_visit",
      visitor_id: "visitor-123",
      qr_slug: "russell-lobby",
      city_slug: "nashville",
    });
  });
});
