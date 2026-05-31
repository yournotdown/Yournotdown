import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export const trackEvent = (event_type, extra = {}) => {
  try {
    api
      .post("/analytics/track", { event_type, ...extra })
      .catch((err) => {
        // Analytics must never break UX — log for observability only.
        if (typeof window !== "undefined" && window.console) {
          console.warn("[analytics] track failed:", event_type, err?.message);
        }
      });
  } catch (e) {
    if (typeof window !== "undefined" && window.console) {
      console.warn("[analytics] track threw:", event_type, e?.message);
    }
  }
};

export const resolveImageUrl = (b) => {
  if (b?.image_path) return `${API}/files/${b.image_path}`;
  if (b?.image_url) return b.image_url;
  if (b?.google_photo_names?.[0]) {
    return `${API}/google-places/photo?photo_name=${encodeURIComponent(b.google_photo_names[0])}`;
  }
  return "";
};
