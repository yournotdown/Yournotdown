const QR_SLUG_KEY = "ynd_qr_slug";
const QR_SCAN_SEEN_PREFIX = "ynd_qr_scan_seen:";

export const normalizeQrSlug = (value) =>
  String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);

export const getCurrentQrSlug = () => {
  if (typeof window === "undefined") {
    return "";
  }
  const localValue = window.localStorage?.getItem(QR_SLUG_KEY);
  if (localValue) {
    return normalizeQrSlug(localValue);
  }
  const sessionValue = window.sessionStorage?.getItem(QR_SLUG_KEY);
  return normalizeQrSlug(sessionValue);
};

export const rememberQrSlugFromSearch = (search = "") => {
  if (typeof window === "undefined") {
    return { qrSlug: "", shouldTrackScan: false };
  }
  const params = new URLSearchParams(search || "");
  const qrSlug = normalizeQrSlug(params.get("qr"));
  if (!qrSlug) {
    return { qrSlug: getCurrentQrSlug(), shouldTrackScan: false };
  }
  window.localStorage?.setItem(QR_SLUG_KEY, qrSlug);
  window.sessionStorage?.setItem(QR_SLUG_KEY, qrSlug);
  const seenKey = `${QR_SCAN_SEEN_PREFIX}${qrSlug}`;
  const alreadyTracked = window.sessionStorage?.getItem(seenKey) === "1";
  if (!alreadyTracked) {
    window.sessionStorage?.setItem(seenKey, "1");
  }
  return {
    qrSlug,
    shouldTrackScan: !alreadyTracked,
  };
};

export { QR_SLUG_KEY, QR_SCAN_SEEN_PREFIX };
