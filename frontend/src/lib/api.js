import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

export const trackEvent = (event_type, extra = {}) => {
  try {
    api.post("/analytics/track", { event_type, ...extra }).catch(() => {});
  } catch (e) {
    /* ignore */
  }
};

export const resolveImageUrl = (b) => {
  if (b?.image_path) return `${API}/files/${b.image_path}`;
  return b?.image_url || "";
};
