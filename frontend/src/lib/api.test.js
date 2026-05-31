jest.mock("axios", () => ({
  create: jest.fn(() => ({
    post: jest.fn(),
  })),
}));

import { API, resolveImageUrl } from "./api";

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
