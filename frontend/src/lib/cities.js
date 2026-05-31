export const DEFAULT_CITY_SLUG = "nashville";

export const activeCitySlug = (citySlug) => citySlug || DEFAULT_CITY_SLUG;

export const cityPath = (citySlug, path = "") => {
  const suffix = path ? `/${path.replace(/^\/+/, "")}` : "";
  return `/${activeCitySlug(citySlug)}${suffix}`;
};

export const cityDisplayName = (citySlug) =>
  activeCitySlug(citySlug)
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
