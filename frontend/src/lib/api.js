import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export const trackEvent = (event_type, extra = {}) => {
  const warn = (msg, err) => {
    if (process.env.NODE_ENV === "development" && typeof window !== "undefined" && window.console) {
      console.warn(msg, event_type, err?.message);
    }
  };
  try {
    api
      .post("/analytics/track", { event_type, ...extra })
      .catch((err) => warn("[analytics] track failed:", err));
  } catch (e) {
    warn("[analytics] track threw:", e);
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
