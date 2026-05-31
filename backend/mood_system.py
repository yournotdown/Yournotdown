"""Mood + tag system for the recommendation engine."""

# All valid tags. Curate this list — admins should pick from these.
TAGS = [
    "coffee", "brunch", "casual", "fine_dining", "dessert", "family", "scenic", "quiet",
    "cocktails", "rooftop", "speakeasy", "live_music", "concerts", "sports",
    "nightlife", "club", "late_night", "entertainment", "date_night", "honky_tonk",
    "popular", "tourist_favorite", "local_favorite",
    "hidden_gem", "unique", "wildcard",
]

# Mood → tag bonuses/penalties.
# `relevance = max(0.05, 1 + sum(weight for tag in business.tags if tag in mood_weights))`
# Final selection weight = relevance * sponsor_multiplier (1/5/10/20).
MOOD_WEIGHTS = {
    # 😇 TAKE IT EASY — relaxed, low-pressure
    "just-vibing": {
        "coffee": 5, "brunch": 5, "family": 5, "dessert": 4, "scenic": 4,
        "casual": 3, "quiet": 3, "local_favorite": 2,
        "nightlife": -10, "club": -10, "late_night": -5,
        "concerts": -2,
    },
    # 😏 LET'S SEE WHERE THIS GOES — social, open-ended
    "down": {
        "date_night": 6, "cocktails": 5, "rooftop": 5, "live_music": 4,
        "speakeasy": 3, "hidden_gem": 2, "local_favorite": 2,
        "family": -3,
    },
    # 🔥 LET'S MAKE IT COUNT — memorable, high energy
    "very-down": {
        "nightlife": 6, "popular": 5, "concerts": 5, "rooftop": 4,
        "entertainment": 4, "tourist_favorite": 3, "late_night": 3,
        "club": 3, "live_music": 3,
        "quiet": -4, "coffee": -3, "family": -4,
    },
    # 🚀 NO REGRETS — maximum adventure, wildcards
    "send-it": {
        "wildcard": 10, "hidden_gem": 8, "unique": 8, "local_favorite": 6,
        "late_night": 5, "nightlife": 4, "speakeasy": 3,
        "tourist_favorite": -2, "casual": -2, "coffee": -2,
    },
}

# Sponsor tier multipliers (applied AFTER relevance so monetization can't override).
SPONSOR_MULTIPLIERS = {"none": 1, "silver": 5, "gold": 10, "platinum": 20}

# Backfill: business name → tag list (idempotent migration source)
NAME_TO_TAGS = {
    "Hattie B's Hot Chicken": ["casual", "tourist_favorite", "popular"],
    "Husk Nashville": ["fine_dining", "date_night", "local_favorite"],
    "The Pharmacy Burger": ["casual", "family", "popular", "local_favorite"],
    "Rolf and Daughters": ["fine_dining", "date_night", "hidden_gem"],
    "Attaboy": ["cocktails", "hidden_gem", "date_night", "local_favorite", "speakeasy"],
    "The Patterson House": ["cocktails", "date_night", "speakeasy", "hidden_gem"],
    "Bastion": ["cocktails", "hidden_gem", "unique", "speakeasy"],
    "Old Glory": ["cocktails", "unique", "date_night"],
    "The Bluebird Cafe": ["live_music", "quiet", "scenic", "local_favorite"],
    "Exit/In": ["live_music", "nightlife", "concerts"],
    "The Basement East": ["live_music", "nightlife", "concerts", "local_favorite"],
    "Ryman Auditorium": ["live_music", "concerts", "tourist_favorite", "scenic", "popular"],
    "Catbird Seat": ["fine_dining", "date_night", "unique", "hidden_gem"],
    "Rooftop at Bobby": ["rooftop", "cocktails", "date_night", "scenic"],
    "Henrietta Red": ["fine_dining", "date_night", "cocktails"],
    "Adventure Science Center": ["family", "scenic"],
    "Nashville Zoo at Grassmere": ["family", "scenic"],
    "Cheekwood Estate & Gardens": ["family", "scenic", "quiet"],
    "Nissan Stadium": ["sports", "popular", "entertainment", "tourist_favorite"],
    "Bridgestone Arena": ["sports", "concerts", "popular", "entertainment"],
    "Geodis Park": ["sports", "popular", "entertainment"],
    "L.A. Jackson": ["rooftop", "cocktails", "scenic", "popular"],
    "White Limozeen": ["rooftop", "cocktails", "unique", "popular"],
    "UP Rooftop Lounge": ["rooftop", "nightlife", "popular"],
    "CMA Fest": ["concerts", "entertainment", "popular", "tourist_favorite"],
    "Tomato Art Fest": ["entertainment", "unique", "local_favorite", "family"],
    "Live On The Green": ["concerts", "entertainment", "local_favorite", "scenic"],
    "Skull's Rainbow Room": ["unique", "hidden_gem", "live_music", "late_night"],
    "Santa's Pub": ["unique", "hidden_gem", "local_favorite", "late_night"],
    "Dino's": ["casual", "local_favorite", "late_night", "hidden_gem"],
}
