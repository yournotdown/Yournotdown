const VISITOR_ID_KEY = "ynd_visitor_id";

const fallbackVisitorId = () => {
  const random = Math.random().toString(16).slice(2);
  const time = Date.now().toString(16);
  return `${time}-${random}`;
};

export const getVisitorId = () => {
  if (typeof window === "undefined" || !window.localStorage) {
    return "";
  }
  const existing = window.localStorage.getItem(VISITOR_ID_KEY);
  if (existing) {
    return existing;
  }
  const nextId = typeof window.crypto?.randomUUID === "function"
    ? window.crypto.randomUUID()
    : fallbackVisitorId();
  window.localStorage.setItem(VISITOR_ID_KEY, nextId);
  return nextId;
};

export { VISITOR_ID_KEY };
