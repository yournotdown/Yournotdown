import axios from "axios";
import { getVisitorId } from "./visitor";

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
      .post("/analytics/track", { event_type, visitor_id: getVisitorId(), ...extra })
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

export const formatEventSchedule = (event) => {
  if (!event) return "";
  return [event.local_date, event.local_time].filter(Boolean).join(" · ");
};

export const formatEventTime = (value) => {
  if (!value) return "";
  const [hourText = "0", minuteText = "00"] = String(value).split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);
  if (!Number.isFinite(hour) || !Number.isFinite(minute)) {
    return value;
  }
  const suffix = hour >= 12 ? "PM" : "AM";
  const normalizedHour = hour % 12 || 12;
  return `${normalizedHour}:${String(minute).padStart(2, "0")} ${suffix}`;
};

export const matchedEventsForBusinesses = (businesses = []) => {
  const seen = new Set();
  return businesses
    .map((business) => business?.event)
    .filter((event) => {
      const key = event?.id || event?.external_event_id;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
};
