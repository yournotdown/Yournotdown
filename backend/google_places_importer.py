"""Curated Nashville Google Places import pipeline.

The default CLI mode is a paid-API dry run. Use --report-template to inspect the
report shape without a Google API key or network request. Use --apply only after
reviewing a dry-run report.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from urllib import error, request

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        """Minimal local fallback for running the importer without dependencies."""
        if not path.exists():
            return
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_dotenv(Path(__file__).with_name(".env"))

GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1"
CITY_SLUG = "nashville"
TARGET_ZIP_CODES = [
    "37201", "37203", "37204", "37205", "37206", "37207",
    "37208", "37209", "37210", "37211", "37212",
]
ZIP_QUERIES = [
    "best restaurants in {zip_code} Nashville",
    "trendy restaurants in {zip_code} Nashville",
    "cocktail bars in {zip_code} Nashville",
    "speakeasies in {zip_code} Nashville",
    "rooftop bars in {zip_code} Nashville",
    "live music venues in {zip_code} Nashville",
    "nightlife in {zip_code} Nashville",
    "nighttime entertainment in {zip_code} Nashville",
    "date night restaurants in {zip_code} Nashville",
    "hidden gem restaurants in {zip_code} Nashville",
]
DOWNTOWN_QUERIES = ["honky tonks in downtown Nashville"]

MIN_RATING = 4.2
PREFERRED_RATING_COUNT = 100
MIN_BRAND_FIT_SCORE = 70
VALID_IMPORT_STATUSES = {"pending", "approved", "rejected"}
CURATOR_ALLOWLIST_DISPLAY_NAMES = {
    "the chloe nashville restaurant bar": "The Chloe Nashville Restaurant & Bar",
    "le loup": "Le Loup",
    "lion s share": "Lion's Share",
    "thistle and rye": "Thistle and Rye",
    "eddie ate dynamite": "Eddie Ate Dynamite",
    "ofelia": "Ofelia",
    "eleven11": "ELEVEN11",
    "streetcar taps garden": "Streetcar Taps & Garden",
    "two hands": "Two Hands",
    "the henry": "The Henry",
}
CURATOR_ALLOWLIST = set(CURATOR_ALLOWLIST_DISPLAY_NAMES)
BROADWAY_OVERRIDE_DISPLAY_NAMES = {
    "jason aldean s kitchen rooftop bar": "Jason Aldean's Kitchen + Rooftop Bar",
    "luke combs category 10": "Luke Combs Category 10",
    "category 10": "Luke Combs Category 10",
    "morgan wallen s this bar": "Morgan Wallen's This Bar",
    "miranda lambert s casa rosa": "Miranda Lambert's Casa Rosa",
    "ole red": "Ole Red",
    "chief s": "Chief's",
    "luke s 32 bridge": "Luke's 32 Bridge",
    "acme feed seed": "Acme Feed & Seed",
    "nashville underground": "Nashville Underground",
    "jbj s nashville": "JBJ's Nashville",
    "tootsies": "Tootsies",
    "robert s western world": "Robert's Western World",
    "legends corner": "Legends Corner",
    "the stage": "The Stage",
    "layla s": "Layla's",
    "nudie s": "Nudie's",
    "aj s good time bar": "AJ's Good Time Bar",
    "friends in low places": "Friends In Low Places",
    "honky tonk central": "Honky Tonk Central",
    "redneck riviera": "Redneck Riviera",
    "rippy s": "Rippy's",
}
BROADWAY_QUERIES = [
    f"{display_name} Nashville"
    for display_name in dict.fromkeys(BROADWAY_OVERRIDE_DISPLAY_NAMES.values())
]
BROADWAY_OVERRIDE_NAMES = list(dict.fromkeys(BROADWAY_OVERRIDE_DISPLAY_NAMES.values()))

DETAIL_FIELDS = [
    "id", "displayName", "formattedAddress", "rating", "userRatingCount",
    "types", "primaryType", "googleMapsUri", "websiteUri",
    "nationalPhoneNumber", "editorialSummary", "photos",
]
DETAIL_FIELD_MASK = ",".join(DETAIL_FIELDS)
SEARCH_FIELD_MASK = ",".join(f"places.{field}" for field in DETAIL_FIELDS)

BLOCKED_TYPES = {
    "gas_station", "convenience_store", "car_wash", "car_repair",
    "grocery_store", "supermarket", "pharmacy", "food_court",
}
ADULT_VENUE_TERMS = {
    "adult entertainment", "gentlemen s club", "hustler club", "strip club",
}
FAST_FOOD_TYPES = {"fast_food_restaurant"}
BLOCKED_NAME_TERMS = {
    "mcdonald", "burger king", "wendy", "taco bell", "subway", "sonic",
    "chick-fil-a", "chipotle", "starbucks", "dunkin", "domino", "pizza hut",
    "papa john", "little caesars", "waffle house", "cracker barrel",
    "applebee", "chili's", "olive garden", "ihop", "denny", "panera",
    "jersey mike", "jimmy john", "five guys", "zaxby", "bojangles",
    "raising cane", "smoothie king", "dairy queen", "hardee", "arby",
    "kfc", "popeyes", "wingstop", "jersey mike", "firehouse subs",
    "maggiano", "stoney river", "cheesecake factory", "yard house",
    "hard rock cafe", "rainforest cafe", "california pizza kitchen",
    "buffalo wild wings", "hooters", "longhorn steakhouse", "outback steakhouse",
    "texas roadhouse", "red lobster", "p f chang", "bonefish grill",
    "first watch", "another broken egg", "true food kitchen", "bartaco",
    "shake shack", "in n out", "whataburger", "panda express", "sweetgreen",
    "cava", "qdoba", "moe s southwest", "noodles company", "potbelly",
    "einstein bros", "krispy kreme", "caribou coffee", "coffee bean",
    "dutch bros", "scooter s coffee", "tim hortons",
}
AIRPORT_TERMS = {"airport", "bna", "concourse", "airpark"}
MALL_TERMS = {"mall", "food court", "opry mills", "shopping center", "shopping centre"}
HOTEL_TERMS = {"hotel", "resort", "inn", "suites", "marriott", "hilton", "hyatt", "sheraton"}
NOTABLE_HOTEL_VENUE_TERMS = {"rooftop", "bar", "lounge", "restaurant", "kitchen", "club"}
EXPERIENCE_TERMS = {
    "rooftop", "honky tonk", "speakeasy", "music", "auditorium",
    "theater", "theatre", "stadium", "arena",
    "distillery", "winery", "brewery", "burlesque", "arcade", "bowling",
}
DAYTIME_ONLY_TYPES = {
    "museum", "park", "zoo", "historical_landmark", "historical_place",
    "visitor_center", "science_museum",
}
NIGHTLIFE_TYPES = {
    "restaurant", "fine_dining_restaurant", "american_restaurant",
    "seafood_restaurant", "steak_house", "italian_restaurant", "bar",
    "cocktail_bar", "wine_bar", "pub", "brewery", "night_club",
    "live_music_venue", "concert_hall", "performing_arts_theater",
    "comedy_club", "event_venue", "stadium", "sports_complex",
    "movie_theater", "bowling_alley",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def normalize_name_address(name: str, address: str) -> str:
    return f"{normalize_text(name)}|{normalize_text(address)}"


def target_zip_code(place: dict) -> Optional[str]:
    address = place.get("formattedAddress", "")
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
    return match.group(1) if match else None


def is_nashville_address(place: dict) -> bool:
    return "nashville tn" in normalize_text(place.get("formattedAddress", ""))


def get_name(place: dict) -> str:
    display_name = place.get("displayName") or {}
    if isinstance(display_name, dict):
        return display_name.get("text", "")
    return str(display_name)


def curator_allowlist_key(place: dict) -> Optional[str]:
    normalized_name = normalize_text(get_name(place))
    return next(
        (
            allowlisted_name
            for allowlisted_name in CURATOR_ALLOWLIST
            if normalized_name == allowlisted_name
            or normalized_name.startswith(f"{allowlisted_name} ")
        ),
        None,
    )


def is_curator_allowlisted(place: dict) -> bool:
    return curator_allowlist_key(place) is not None


def broadway_override_key(place: dict) -> Optional[str]:
    normalized_name = normalize_text(get_name(place))
    return next(
        (
            override_name
            for override_name in BROADWAY_OVERRIDE_DISPLAY_NAMES
            if normalized_name == override_name
            or normalized_name.startswith(f"{override_name} ")
        ),
        None,
    )


def is_broadway_override(place: dict) -> bool:
    return broadway_override_key(place) is not None


def import_override_reason(place: dict) -> Optional[str]:
    if is_broadway_override(place):
        return "broadway_override"
    if is_curator_allowlisted(place):
        return "curator_allowlist"
    return None


def is_nightlife_inventory(place: dict) -> bool:
    types = set(place.get("types") or [])
    text = normalize_text(
        " ".join(
            [
                get_name(place),
                (place.get("editorialSummary") or {}).get("text", "")
                if isinstance(place.get("editorialSummary") or {}, dict)
                else str(place.get("editorialSummary") or ""),
            ]
        )
    )
    return bool(
        types & NIGHTLIFE_TYPES
        or any(
            term in text
            for term in {
                "rooftop", "honky tonk", "speakeasy", "brewery", "live music",
                "nightlife", "cocktail", "late night", "lounge", "saloon",
            }
        )
    )


def should_import_place(place: dict) -> tuple[bool, str]:
    """Apply the hard quality filter before a place enters admin review."""
    name = get_name(place)
    rating = float(place.get("rating") or 0)
    rating_count = int(place.get("userRatingCount") or 0)
    types = set(place.get("types") or [])
    normalized_name = normalize_text(name)
    normalized_address = normalize_text(place.get("formattedAddress", ""))
    searchable_text = f"{normalized_name} {normalized_address}"

    if not place.get("id") or not name:
        return False, "missing_identity"
    if target_zip_code(place) not in TARGET_ZIP_CODES and not (
        is_broadway_override(place) and is_nashville_address(place)
    ):
        return False, "outside_target_zip_codes"
    if rating < MIN_RATING:
        return False, "rating_below_4_2"
    if types & BLOCKED_TYPES:
        return False, "blocked_place_type"
    if any(term in searchable_text for term in ADULT_VENUE_TERMS):
        return False, "adult_venue"
    if types & FAST_FOOD_TYPES:
        return False, "fast_food"
    if any(term in normalized_name for term in BLOCKED_NAME_TERMS):
        return False, "excluded_chain"
    if any(term in normalized_address for term in AIRPORT_TERMS) or any(
        term in normalized_name for term in {"airport", "bna", "concourse"}
    ):
        return False, "airport_food"
    if any(term in searchable_text for term in MALL_TERMS):
        return False, "mall_food"
    if "lodging" in types and not (
        types & {"bar", "cocktail_bar", "restaurant", "tourist_attraction"}
        or any(term in normalized_name for term in NOTABLE_HOTEL_VENUE_TERMS)
    ):
        return False, "hotel_without_notable_venue"
    if types & DAYTIME_ONLY_TYPES and not is_nightlife_inventory(place):
        return False, "daytime_only_attraction"
    if not is_nightlife_inventory(place):
        return False, "not_nightlife_inventory"
    if any(term in normalized_name for term in HOTEL_TERMS) and not (
        types & {"bar", "cocktail_bar", "restaurant", "tourist_attraction"}
        or any(term in normalized_name for term in NOTABLE_HOTEL_VENUE_TERMS)
    ):
        return False, "hotel_without_notable_venue"
    if rating_count < PREFERRED_RATING_COUNT and not import_override_reason(place):
        return False, "rating_count_below_100"
    return True, "accepted"


def assign_tags(place: dict, source_queries: Iterable[str]) -> list[str]:
    """Infer editorial tags from Google metadata and discovery context."""
    name = normalize_text(get_name(place))
    address = normalize_text(place.get("formattedAddress", ""))
    summary = place.get("editorialSummary") or {}
    summary_text = summary.get("text", "") if isinstance(summary, dict) else str(summary)
    types = set(place.get("types") or [])
    text = " ".join([name, address, normalize_text(summary_text)])
    query_text = normalize_text(" ".join(source_queries))
    rating_count = int(place.get("userRatingCount") or 0)
    tags = set()

    if "coffee_shop" in types or "cafe" in types:
        tags.add("coffee")
    if "brunch" in text:
        tags.add("brunch")
    if {"bar", "cocktail_bar"} & types or "cocktail" in text or "cocktail bars" in query_text:
        tags.add("cocktails")
    if "rooftop" in text or "rooftop bars" in query_text:
        tags.update({"rooftop", "scenic"})
    if "speakeasy" in text or "speakeasies" in query_text:
        tags.update({"speakeasy", "hidden_gem", "unique"})
    if "honky tonk" in text:
        tags.update({"honky_tonk", "live_music", "nightlife", "late_night", "tourist_favorite"})
    if {"live_music_venue", "concert_hall", "performing_arts_theater"} & types or "live music" in text or "live music venues" in query_text:
        tags.update({"live_music", "entertainment"})
    if {"night_club", "bar"} & types or "nightlife" in text:
        tags.add("nightlife")
    if "night_club" in types or "late night" in text or "honky_tonk" in tags:
        tags.add("late_night")
    if "hidden gem" in text or "secret" in text:
        tags.update({"hidden_gem", "local_favorite"})
    if "date night" in text or "date night" in query_text or "fine_dining_restaurant" in types or "romantic" in text:
        tags.add("date_night")
    if "fine_dining_restaurant" in types:
        tags.add("fine_dining")
    if {"stadium", "sports_club", "sports_complex"} & types:
        tags.update({"sports", "entertainment"})
    if "rooftop" in tags:
        tags.add("scenic")
    if is_broadway_override(place):
        tags.update({"broadway", "nightlife", "tourist_favorite"})
    if rating_count >= 500:
        tags.add("popular")
    if rating_count >= 100 and "tourist_favorite" not in tags:
        tags.add("local_favorite")
    if "unique" in text:
        tags.add("unique")
    return sorted(tags)


def brand_fit_score(place: dict, tags: Iterable[str], source_queries: Iterable[str]) -> int:
    """Score Nashville nightlife and destination fit from 1 to 100."""
    tags = set(tags)
    types = set(place.get("types") or [])
    name = normalize_text(get_name(place))
    summary = place.get("editorialSummary") or {}
    summary_text = summary.get("text", "") if isinstance(summary, dict) else str(summary)
    text = f"{name} {normalize_text(summary_text)}"
    query_text = normalize_text(" ".join(source_queries))
    rating = float(place.get("rating") or 0)
    rating_count = int(place.get("userRatingCount") or 0)
    score = 18

    score += 8 if rating >= 4.2 else 0
    score += 4 if rating >= 4.5 else 0
    score += 4 if rating >= 4.7 else 0
    score += 3 if rating >= 4.9 else 0
    if rating_count >= 7500:
        score += 18
    elif rating_count >= 3000:
        score += 15
    elif rating_count >= 1000:
        score += 12
    elif rating_count >= 500:
        score += 9
    elif rating_count >= 250:
        score += 6
    else:
        score += 3

    bonuses = {
        "tourist_favorite": 13, "honky_tonk": 18, "rooftop": 14,
        "speakeasy": 14, "live_music": 13, "unique": 11, "hidden_gem": 8,
        "date_night": 7, "late_night": 6, "nightlife": 5,
        "local_favorite": 4, "entertainment": 4, "scenic": 3, "cocktails": 3,
    }
    score += sum(bonuses.get(tag, 0) for tag in tags)
    if types & {"stadium", "concert_hall", "live_music_venue"}:
        score += 9
    if any(term in text for term in EXPERIENCE_TERMS):
        score += 6
    if any(term in query_text for term in {"trendy", "hidden gem", "date night"}):
        score += 2

    # Plain restaurants need a stronger signal than rating alone.
    restaurant_types = {"restaurant", "american_restaurant", "italian_restaurant",
                        "seafood_restaurant", "steak_house"}
    if types & restaurant_types and not tags & {
        "date_night", "fine_dining", "live_music", "rooftop", "unique",
        "hidden_gem", "tourist_favorite", "local_favorite",
    }:
        score -= 18
    if "coffee" in tags and not tags & {"unique", "hidden_gem", "tourist_favorite"}:
        score -= 15
    return max(1, min(100, score))


def assign_slots(place: dict, tags: Iterable[str]) -> list[str]:
    """Assign itinerary slots using Google types and inferred editorial tags."""
    types = set(place.get("types") or [])
    tags = set(tags)
    slots = set()

    if types & {"restaurant", "fine_dining_restaurant", "american_restaurant",
                "seafood_restaurant", "steak_house", "italian_restaurant"}:
        slots.add("dinner")
    if types & {"bar", "cocktail_bar", "wine_bar", "pub"} or tags & {
        "cocktails", "rooftop", "speakeasy", "honky_tonk",
    }:
        slots.add("drinks")
    if types & {
        "live_music_venue", "concert_hall", "performing_arts_theater",
        "stadium", "sports_complex", "night_club", "comedy_club", "event_venue",
    } or tags & {"live_music", "entertainment", "sports"}:
        slots.add("entertainment")
    if types & {"night_club", "bar", "cocktail_bar", "pub"} or tags & {
        "late_night", "nightlife", "honky_tonk",
    }:
        slots.add("late-night")
    return [slot for slot in ["dinner", "drinks", "entertainment", "late-night"] if slot in slots]


def category_for_place(place: dict, tags: Iterable[str]) -> str:
    types = set(place.get("types") or [])
    tags = set(tags)
    if tags & {"nightlife", "late_night", "honky_tonk", "rooftop"} or "night_club" in types:
        return "night-out"
    if tags & {"live_music", "entertainment"}:
        return "live-music"
    if tags & {"cocktails", "speakeasy"} or "bar" in types:
        return "drinks"
    return "date-night"


def nightlife_categories(place: dict, tags: Iterable[str]) -> list[str]:
    types = set(place.get("types") or [])
    tags = set(tags)
    categories = set()
    if "broadway" in tags:
        categories.add("Broadway")
    if "rooftop" in tags:
        categories.add("Rooftop")
    if "cocktails" in tags or types & {"bar", "cocktail_bar", "wine_bar", "pub"}:
        categories.add("Cocktail")
    if "speakeasy" in tags:
        categories.add("Speakeasy")
    if "live_music" in tags or types & {"live_music_venue", "concert_hall"}:
        categories.add("Live Music")
    if "date_night" in tags or "fine_dining_restaurant" in types:
        categories.add("Date Night")
    if "late_night" in tags:
        categories.add("Late Night Food")
    if not categories or "unique" in tags or "hidden_gem" in tags:
        categories.add("Wildcard")
    return [
        category for category in [
            "Broadway", "Rooftop", "Cocktail", "Speakeasy", "Live Music",
            "Date Night", "Late Night Food", "Wildcard",
        ]
        if category in categories
    ]


def photo_resource_names(place: dict) -> list[str]:
    return [photo["name"] for photo in place.get("photos") or [] if photo.get("name")][:10]


def build_business_document(place: dict, source_queries: Iterable[str]) -> dict:
    tags = assign_tags(place, source_queries)
    slots = assign_slots(place, tags)
    fit_score = brand_fit_score(place, tags, source_queries)
    override_reason = import_override_reason(place)
    summary = place.get("editorialSummary") or {}
    return {
        "name": get_name(place),
        "description": summary.get("text", "") if isinstance(summary, dict) else str(summary),
        "image_url": "",
        "image_path": None,
        "website": place.get("websiteUri", ""),
        "phone": place.get("nationalPhoneNumber", ""),
        "address": place.get("formattedAddress", ""),
        "category_slug": category_for_place(place, tags),
        "city_slug": CITY_SLUG,
        "featured": False,
        "sponsor_tier": "none",
        "slots": slots,
        "tags": tags,
        "nightlife_categories": nightlife_categories(place, tags),
        "brand_fit_score": fit_score,
        "import_override_reason": override_reason,
        "google_place_id": place["id"],
        "normalized_name_address": normalize_name_address(
            get_name(place), place.get("formattedAddress", "")
        ),
        "google_rating": float(place.get("rating") or 0),
        "google_user_rating_count": int(place.get("userRatingCount") or 0),
        "google_maps_url": place.get("googleMapsUri", ""),
        "google_photo_names": photo_resource_names(place),
        "google_types": sorted(set(place.get("types") or [])),
        "imported_status": "pending",
        "import_source": "google_places",
        "imported_at": now_iso(),
        "import_queries": sorted(set(source_queries)),
        "order": 0,
        "created_at": now_iso(),
        "id": str(uuid.uuid4()),
    }


def dedupe_key(document: dict) -> str:
    return document.get("normalized_name_address") or normalize_name_address(
        document.get("name", ""), document.get("address", "")
    )


def dedupe_documents(documents: Iterable[dict], existing: Iterable[dict] = ()) -> tuple[list[dict], list[dict]]:
    seen_place_ids = {row.get("google_place_id") for row in existing if row.get("google_place_id")}
    seen_name_addresses = {dedupe_key(row) for row in existing if row.get("name") and row.get("address")}
    unique = []
    duplicates = []
    for document in documents:
        place_id = document.get("google_place_id")
        name_address = dedupe_key(document)
        if place_id in seen_place_ids or name_address in seen_name_addresses:
            duplicates.append(document)
            continue
        unique.append(document)
        if place_id:
            seen_place_ids.add(place_id)
        seen_name_addresses.add(name_address)
    return unique, duplicates


def report_template(dry_run: bool = True) -> dict:
    return {
        "mode": "dry-run" if dry_run else "apply",
        "city_slug": CITY_SLUG,
        "zip_codes": list(TARGET_ZIP_CODES),
        "queries_planned": len(TARGET_ZIP_CODES) * len(ZIP_QUERIES) + len(DOWNTOWN_QUERIES) + len(BROADWAY_QUERIES),
        "minimum_brand_fit_score": MIN_BRAND_FIT_SCORE,
        "curator_allowlist": sorted(CURATOR_ALLOWLIST),
        "curator_allowlist_results": [],
        "broadway_override_results": [],
        "nightlife_inventory": {
            "total_nightlife_venues": 0,
            "broadway_venues": 0,
            "rooftops": 0,
            "cocktail_bars": 0,
            "date_night_restaurants": 0,
            "speakeasies": 0,
            "live_music_venues": 0,
        },
        "found": 0,
        "details_fetched": 0,
        "skipped": 0,
        "skipped_by_reason": {},
        "duplicated": 0,
        "pending": 0,
        "approved": 0,
        "inserted": 0,
        "candidate_pool_by_slot": {
            "dinner": 0, "drinks": 0, "entertainment": 0, "late-night": 0,
        },
        "top_pending_candidates": [],
        "bottom_rejected_candidates": [],
    }


class GooglePlacesClient:
    def __init__(self, api_key: Optional[str] = None, session=None):
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise RuntimeError("GOOGLE_PLACES_API_KEY must be set")
        if session is None:
            try:
                import requests

                session = requests.Session()
            except ImportError:
                session = StandardLibrarySession()
        self.session = session

    def _headers(self, field_mask: str) -> dict:
        return {"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": field_mask}

    def search_text(self, query: str, page_size: int = 20) -> list[dict]:
        response = self._request_with_retry(
            self.session.post,
            f"{GOOGLE_PLACES_API_URL}/places:searchText",
            headers=self._headers(SEARCH_FIELD_MASK),
            json={"textQuery": query, "pageSize": min(page_size, 20)},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("places", [])

    def place_details(self, place_id: str) -> dict:
        response = self._request_with_retry(
            self.session.get,
            f"{GOOGLE_PLACES_API_URL}/places/{place_id}",
            headers=self._headers(DETAIL_FIELD_MASK),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _request_with_retry(method, url, attempts=3, **kwargs):
        for attempt in range(1, attempts + 1):
            try:
                response = method(url, **kwargs)
                response.raise_for_status()
                return response
            except Exception:
                if attempt == attempts:
                    raise
                time.sleep(attempt)


class StandardLibraryResponse:
    def __init__(self, response):
        self.status_code = response.status
        self._body = response.read()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"Google Places API returned HTTP {self.status_code}")

    def json(self):
        return json.loads(self._body.decode("utf-8"))


class StandardLibrarySession:
    """Small requests-compatible fallback for the standalone importer CLI."""
    @staticmethod
    def post(url, headers, json, timeout):
        body = __import__("json").dumps(json).encode("utf-8")
        req = request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
        return StandardLibrarySession._open(req, timeout)

    @staticmethod
    def get(url, headers, timeout):
        return StandardLibrarySession._open(request.Request(url, headers=headers, method="GET"), timeout)

    @staticmethod
    def _open(req, timeout):
        try:
            return StandardLibraryResponse(request.urlopen(req, timeout=timeout))
        except error.HTTPError as exc:
            return StandardLibraryResponse(exc)


def planned_queries(zip_codes: Iterable[str]) -> list[str]:
    return [
        *(template.format(zip_code=zip_code) for zip_code in zip_codes for template in ZIP_QUERIES),
        *DOWNTOWN_QUERIES,
        *BROADWAY_QUERIES,
    ]


def run_import(client: GooglePlacesClient, existing: Iterable[dict] = (), collection=None,
               dry_run: bool = True, zip_codes: Iterable[str] = TARGET_ZIP_CODES,
               query_limit: Optional[int] = None) -> dict:
    """Discover, enrich, filter, dedupe, and optionally persist pending places."""
    report = report_template(dry_run=dry_run)
    query_sources = {}
    queries = planned_queries(zip_codes)
    if query_limit is not None:
        queries = queries[:query_limit]
    report["queries_planned"] = len(queries)

    for query in queries:
        for place in client.search_text(query):
            place_id = place.get("id")
            if place_id:
                query_sources.setdefault(place_id, set()).add(query)
    report["found"] = len(query_sources)

    skipped = Counter()
    candidates = []
    rejected = []
    curator_allowlist_results = {}
    broadway_override_results = {}
    for place_id, source_queries in query_sources.items():
        place = client.place_details(place_id)
        report["details_fetched"] += 1
        allowlist_key = curator_allowlist_key(place)
        broadway_key = broadway_override_key(place)
        broadway_name = BROADWAY_OVERRIDE_DISPLAY_NAMES.get(broadway_key)
        accepted, reason = should_import_place(place)
        if not accepted:
            skipped[reason] += 1
            rejected_candidate = rejection_summary(place, reason, source_queries)
            rejected.append(rejected_candidate)
            if allowlist_key:
                curator_allowlist_results[allowlist_key] = {
                    "included": False,
                    **rejected_candidate,
                }
            if broadway_name and not broadway_override_results.get(broadway_name, {}).get("included"):
                broadway_override_results[broadway_name] = {
                    "included": False,
                    **rejected_candidate,
                }
            continue
        document = build_business_document(place, source_queries)
        if not document["slots"]:
            skipped["no_itinerary_slots"] += 1
            rejected_candidate = rejection_summary(place, "no_itinerary_slots", source_queries)
            rejected.append(rejected_candidate)
            if allowlist_key:
                curator_allowlist_results[allowlist_key] = {
                    "included": False,
                    **rejected_candidate,
                }
            if broadway_name and not broadway_override_results.get(broadway_name, {}).get("included"):
                broadway_override_results[broadway_name] = {
                    "included": False,
                    **rejected_candidate,
                }
            continue
        if document["brand_fit_score"] < MIN_BRAND_FIT_SCORE and not document["import_override_reason"]:
            skipped["brand_fit_below_70"] += 1
            rejected_candidate = rejection_summary(place, "brand_fit_below_70", source_queries)
            rejected.append(rejected_candidate)
            if allowlist_key:
                curator_allowlist_results[allowlist_key] = {
                    "included": False,
                    **rejected_candidate,
                }
            if broadway_name and not broadway_override_results.get(broadway_name, {}).get("included"):
                broadway_override_results[broadway_name] = {
                    "included": False,
                    **rejected_candidate,
                }
            continue
        candidates.append(document)
        if allowlist_key:
            curator_allowlist_results[allowlist_key] = {
                "name": document["name"],
                "included": True,
                "import_override_reason": document["import_override_reason"],
                "brand_fit_score": document["brand_fit_score"],
                "rating": document["google_rating"],
                "userRatingCount": document["google_user_rating_count"],
                "slots": document["slots"],
            }
        if broadway_name:
            broadway_override_results[broadway_name] = {
                "name": document["name"],
                "included": True,
                "import_override_reason": document["import_override_reason"],
                "brand_fit_score": document["brand_fit_score"],
                "rating": document["google_rating"],
                "userRatingCount": document["google_user_rating_count"],
                "slots": document["slots"],
            }

    unique, duplicates = dedupe_documents(candidates, existing)
    if not dry_run:
        if collection is None:
            raise RuntimeError("Mongo collection is required when --apply is used")
        for document in unique:
            collection.insert_one(document)

    report["skipped"] = sum(skipped.values())
    report["skipped_by_reason"] = dict(sorted(skipped.items()))
    report["duplicated"] = len(duplicates)
    report["pending"] = len(unique)
    report["inserted"] = 0 if dry_run else len(unique)
    report["candidate_pool_by_slot"] = {
        slot: sum(slot in row["slots"] for row in unique)
        for slot in ["dinner", "drinks", "entertainment", "late-night"]
    }
    category_counts = Counter(
        category
        for row in unique
        for category in row["nightlife_categories"]
    )
    report["nightlife_inventory"] = {
        "total_nightlife_venues": len(unique),
        "broadway_venues": category_counts["Broadway"],
        "rooftops": category_counts["Rooftop"],
        "cocktail_bars": category_counts["Cocktail"],
        "date_night_restaurants": category_counts["Date Night"],
        "speakeasies": category_counts["Speakeasy"],
        "live_music_venues": category_counts["Live Music"],
    }
    report["top_pending_candidates"] = [
        {
            "name": row["name"],
            "google_place_id": row["google_place_id"],
            "brand_fit_score": row["brand_fit_score"],
            "import_override_reason": row["import_override_reason"],
            "rating": row["google_rating"],
            "userRatingCount": row["google_user_rating_count"],
            "address": row["address"],
            "tags": row["tags"],
            "nightlife_categories": row["nightlife_categories"],
            "slots": row["slots"],
            "imported_status": row["imported_status"],
        }
        for row in sorted(unique, key=lambda item: (-item["brand_fit_score"], item["name"]))[:50]
    ]
    report["curator_allowlist_results"] = [
        curator_allowlist_results.get(
            allowlisted_name,
            {
                "name": display_name,
                "included": False,
                "rejection_reason": "not_discovered",
            },
        )
        for allowlisted_name, display_name in CURATOR_ALLOWLIST_DISPLAY_NAMES.items()
    ]
    report["broadway_override_results"] = [
        broadway_override_results.get(
            display_name,
            {
                "name": display_name,
                "included": False,
                "rejection_reason": "not_discovered",
            },
        )
        for display_name in BROADWAY_OVERRIDE_NAMES
    ]
    report["bottom_rejected_candidates"] = sorted(
        rejected,
        key=lambda item: (item["brand_fit_score"], item["name"]),
    )[:25]
    return report


def rejection_summary(place: dict, reason: str, source_queries: Iterable[str]) -> dict:
    tags = assign_tags(place, source_queries)
    return {
        "name": get_name(place),
        "google_place_id": place.get("id"),
        "brand_fit_score": brand_fit_score(place, tags, source_queries),
        "rating": float(place.get("rating") or 0),
        "userRatingCount": int(place.get("userRatingCount") or 0),
        "address": place.get("formattedAddress", ""),
        "rejection_reason": reason,
    }


def mongo_business_collection():
    from pymongo import MongoClient

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        raise RuntimeError("MONGO_URL and DB_NAME must be set when --apply is used")
    return MongoClient(mongo_url)[db_name].businesses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Discover and report candidates without inserting rows")
    parser.add_argument("--apply", action="store_true", help="Insert accepted places as pending review")
    parser.add_argument("--report-template", action="store_true", help="Print report shape without API calls")
    parser.add_argument("--query-limit", type=int, help="Limit discovery queries for a small paid smoke test")
    parser.add_argument("--zip-code", action="append", dest="zip_codes", help="Override target ZIP codes")
    args = parser.parse_args()
    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply cannot be used together")

    if args.report_template:
        print(json.dumps(report_template(dry_run=not args.apply), indent=2))
        return

    has_mongo_config = os.environ.get("MONGO_URL") and os.environ.get("DB_NAME")
    collection = mongo_business_collection() if args.apply or has_mongo_config else None
    existing = list(collection.find({}, {"_id": 0})) if collection is not None else []
    report = run_import(
        GooglePlacesClient(),
        existing=existing,
        collection=collection,
        dry_run=not args.apply,
        zip_codes=args.zip_codes or TARGET_ZIP_CODES,
        query_limit=args.query_limit,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
