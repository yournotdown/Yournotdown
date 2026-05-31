"""Seed data for "You're Not Down" — Nashville businesses."""

CATEGORIES = [
    {"slug": "drinks", "name": "Drinks & Conversation", "emoji": "🍸", "order": 1},
    {"slug": "date-night", "name": "Date Night", "emoji": "❤️", "order": 2},
    {"slug": "live-music", "name": "Live Music", "emoji": "🎵", "order": 3},
    {"slug": "night-out", "name": "Night Out", "emoji": "🌃", "order": 4},
    {"slug": "family-fun", "name": "Family Time", "emoji": "👨‍👩‍👧", "order": 5},
    {"slug": "surprise-me", "name": "Surprise Me", "emoji": "🎲", "order": 6},
]

# One-time migration map: old category slug -> new category slug
CATEGORY_MIGRATIONS = {
    "food": "date-night",
    "sports": "night-out",
    "rooftops": "night-out",
    "events": "night-out",
}

REMOVED_CATEGORY_SLUGS = list(CATEGORY_MIGRATIONS.keys())

# Default itinerary slot assignment by canonical category.
SLOTS_BY_CATEGORY = {
    "date-night": ["dinner"],
    "drinks": ["drinks"],
    "live-music": ["entertainment"],
    "night-out": ["late-night"],
    "family-fun": ["entertainment"],
    "surprise-me": ["entertainment", "late-night"],
}


def canonical_category_slug(category_slug):
    """Return the canonical category slug for legacy and current data."""
    return CATEGORY_MIGRATIONS.get(category_slug, category_slug)


def default_slots_for_category(category_slug):
    """Return a fresh default slot list after canonicalizing the category."""
    canonical_slug = canonical_category_slug(category_slug)
    return list(SLOTS_BY_CATEGORY.get(canonical_slug, []))


CITIES = [
    {"slug": "nashville", "name": "Nashville", "default": True},
]

# image references — using design guideline images + curated unsplash
IMG_FOOD = "https://images.unsplash.com/photo-1661422586023-681ea60507e2?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200"
IMG_DRINKS = "https://static.prod-images.emergentagent.com/jobs/b92b0f3b-9cfd-4b9b-83f4-6105a4bdc217/images/c1177e1886d16b846ca25ac0693579cf6c7f3ad7b682268fcfe8e2fb4ed9514d.png"
IMG_MUSIC = "https://static.prod-images.emergentagent.com/jobs/b92b0f3b-9cfd-4b9b-83f4-6105a4bdc217/images/41df6b9a58753125673589ac5cee166fa575f4191a4a3ef3331508da99ced7ee.png"
IMG_DATE = "https://images.unsplash.com/photo-1559329007-40df8a9345d8?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200"
IMG_FAMILY = "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200"
IMG_SPORTS = "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200"
IMG_ROOFTOP = "https://images.unsplash.com/photo-1519214605650-76a613ee3245?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200"
IMG_EVENT = "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200"

BUSINESSES = [
    # FOOD
    {"name": "Hattie B's Hot Chicken", "category_slug": "food", "description": "Nashville's iconic hot chicken — pick your heat, grab a side of mac.", "image_url": IMG_FOOD, "website": "https://hattieb.com", "phone": "+16157426387", "address": "112 19th Ave S, Nashville, TN", "featured": True},
    {"name": "Husk Nashville", "category_slug": "food", "description": "Refined Southern cooking in a restored 19th-century home.", "image_url": IMG_FOOD, "website": "https://husknashville.com", "phone": "+16152567299", "address": "37 Rutledge St, Nashville, TN"},
    {"name": "The Pharmacy Burger", "category_slug": "food", "description": "Burgers, phosphates and a backyard beer garden.", "image_url": IMG_FOOD, "website": "https://thepharmacynashville.com", "phone": "+16152629899", "address": "731 McFerrin Ave, Nashville, TN"},
    {"name": "Rolf and Daughters", "category_slug": "food", "description": "Wood-fired pastas and natural wine in a Germantown warehouse.", "image_url": IMG_FOOD, "website": "https://rolfanddaughters.com", "phone": "+16157264800", "address": "700 Taylor St, Nashville, TN"},

    # DRINKS
    {"name": "Attaboy", "category_slug": "drinks", "description": "Bartender's-choice cocktail den — no menu, just trust.", "image_url": IMG_DRINKS, "website": "https://attaboynashville.com", "phone": "+16158889724", "address": "8 McFerrin Ave, Nashville, TN", "featured": True},
    {"name": "The Patterson House", "category_slug": "drinks", "description": "Speakeasy classics in a curtained back room.", "image_url": IMG_DRINKS, "website": "https://thepattersonnashville.com", "phone": "+16152562222", "address": "1711 Division St, Nashville, TN"},
    {"name": "Bastion", "category_slug": "drinks", "description": "Tiny bar, big cocktails, hidden behind the nachos.", "image_url": IMG_DRINKS, "website": "https://bastionnashville.com", "phone": "+16156019293", "address": "434 Houston St, Nashville, TN"},
    {"name": "Old Glory", "category_slug": "drinks", "description": "Cathedral-like cocktail lounge in a former boiler room.", "image_url": IMG_DRINKS, "website": "https://oldglorynashville.com", "phone": "+16153794200", "address": "1200 Villa Pl, Nashville, TN"},

    # LIVE MUSIC
    {"name": "The Bluebird Cafe", "category_slug": "live-music", "description": "Songwriters in the round. The Nashville listening room.", "image_url": IMG_MUSIC, "website": "https://bluebirdcafe.com", "phone": "+16153831461", "address": "4104 Hillsboro Pike, Nashville, TN", "featured": True},
    {"name": "Exit/In", "category_slug": "live-music", "description": "Legendary rock club that's hosted everyone from Etta to Etta.", "image_url": IMG_MUSIC, "website": "https://exitin.com", "phone": "+16153213340", "address": "2208 Elliston Pl, Nashville, TN"},
    {"name": "The Basement East", "category_slug": "live-music", "description": "Indie shows, late nights, sweaty crowds.", "image_url": IMG_MUSIC, "website": "https://thebasementeast.com", "phone": "+16158437620", "address": "917 Woodland St, Nashville, TN"},
    {"name": "Ryman Auditorium", "category_slug": "live-music", "description": "The Mother Church. Pews, stained glass, perfect acoustics.", "image_url": IMG_MUSIC, "website": "https://ryman.com", "phone": "+16158897464", "address": "116 Rep. John Lewis Way N, Nashville, TN"},

    # DATE NIGHT
    {"name": "Catbird Seat", "category_slug": "date-night", "description": "Chef's counter with a multi-course tasting menu.", "image_url": IMG_DATE, "website": "https://thecatbirdseatrestaurant.com", "phone": "+16159658511", "address": "1711 Division St, Nashville, TN", "featured": True},
    {"name": "Rooftop at Bobby", "category_slug": "date-night", "description": "Vintage bus, skyline views, low-light cocktails.", "image_url": IMG_ROOFTOP, "website": "https://bobbyhotel.com", "phone": "+16152442020", "address": "230 4th Ave N, Nashville, TN"},
    {"name": "Henrietta Red", "category_slug": "date-night", "description": "Raw bar, natural wine, soft glowing dining room.", "image_url": IMG_DATE, "website": "https://henriettared.com", "phone": "+16157255600", "address": "1200 4th Ave N, Nashville, TN"},

    # FAMILY FUN
    {"name": "Adventure Science Center", "category_slug": "family-fun", "description": "Hands-on exhibits and a planetarium with a panoramic dome.", "image_url": IMG_FAMILY, "website": "https://adventuresci.org", "phone": "+16158628881", "address": "800 Fort Negley Blvd, Nashville, TN"},
    {"name": "Nashville Zoo at Grassmere", "category_slug": "family-fun", "description": "200 acres, jungle gym treehouse, kangaroo kickabout.", "image_url": IMG_FAMILY, "website": "https://nashvillezoo.org", "phone": "+16158334224", "address": "3777 Nolensville Pike, Nashville, TN"},
    {"name": "Cheekwood Estate & Gardens", "category_slug": "family-fun", "description": "Mansion, gardens, seasonal lights and weekend programming.", "image_url": IMG_FAMILY, "website": "https://cheekwood.org", "phone": "+16153560092", "address": "1200 Forrest Park Dr, Nashville, TN"},

    # SPORTS
    {"name": "Nissan Stadium", "category_slug": "sports", "description": "Home of the Tennessee Titans. NFL Sundays, riverside views.", "image_url": IMG_SPORTS, "website": "https://nissanstadium.com", "phone": "+16155658600", "address": "1 Titans Way, Nashville, TN", "featured": True},
    {"name": "Bridgestone Arena", "category_slug": "sports", "description": "Catch the Predators or a stadium-size headliner downtown.", "image_url": IMG_SPORTS, "website": "https://bridgestonearena.com", "phone": "+16157707800", "address": "501 Broadway, Nashville, TN"},
    {"name": "Geodis Park", "category_slug": "sports", "description": "Nashville SC's home — chants, smoke, southern fútbol.", "image_url": IMG_SPORTS, "website": "https://geodispark.com", "phone": "+16158228000", "address": "501 Benton Ave, Nashville, TN"},

    # ROOFTOPS
    {"name": "L.A. Jackson", "category_slug": "rooftops", "description": "Glass-walled rooftop above Thompson Hotel. Sunsets and skyline.", "image_url": IMG_ROOFTOP, "website": "https://lajacksonbar.com", "phone": "+16157702008", "address": "401 11th Ave S, Nashville, TN", "featured": True},
    {"name": "White Limozeen", "category_slug": "rooftops", "description": "Hot pink rooftop wonderland on top of Graduate Hotel.", "image_url": IMG_ROOFTOP, "website": "https://whitelimozeen.com", "phone": "+16157612824", "address": "101 20th Ave N, Nashville, TN"},
    {"name": "UP Rooftop Lounge", "category_slug": "rooftops", "description": "Killer views across the Gulch, neon-lit and loud.", "image_url": IMG_ROOFTOP, "website": "https://uprooftoplounge.com", "phone": "+16157770171", "address": "901 Division St, Nashville, TN"},

    # EVENTS
    {"name": "CMA Fest", "category_slug": "events", "description": "Four days of country at every downtown stage. June.", "image_url": IMG_EVENT, "website": "https://cmafest.com", "phone": "+16152442840", "address": "Downtown Nashville, TN", "featured": True},
    {"name": "Tomato Art Fest", "category_slug": "events", "description": "East Nashville's weirdest, friendliest block party. August.", "image_url": IMG_EVENT, "website": "https://tomatoartfest.com", "phone": "+16152627379", "address": "5 Points, East Nashville, TN"},
    {"name": "Live On The Green", "category_slug": "events", "description": "Free outdoor concert series at Public Square Park.", "image_url": IMG_EVENT, "website": "https://liveonthegreen.com", "phone": "+16157379828", "address": "Public Sq, Nashville, TN"},

    # SURPRISE ME (mix)
    {"name": "Skull's Rainbow Room", "category_slug": "surprise-me", "description": "Burlesque, supper club, jazz — Printers Alley after dark.", "image_url": IMG_MUSIC, "website": "https://skullsrainbowroom.com", "phone": "+16157305865", "address": "222 Printers Aly, Nashville, TN", "featured": True},
    {"name": "Santa's Pub", "category_slug": "surprise-me", "description": "Karaoke in a double-wide trailer. No frills, full heart.", "image_url": IMG_DRINKS, "website": "http://santaspub.com", "phone": "+16156497705", "address": "2225 Bransford Ave, Nashville, TN"},
    {"name": "Dino's", "category_slug": "surprise-me", "description": "Cheeseburger, cold beer, neon sign. Don't overthink it.", "image_url": IMG_FOOD, "website": "https://dinosnashville.com", "phone": "+16152273866", "address": "411 Gallatin Ave, Nashville, TN"},
]
