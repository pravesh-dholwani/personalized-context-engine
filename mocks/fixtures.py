"""Fixture data mirroring the assignment brief's sample payloads. Any
userId other than user_101 gets the same fixture back with its id swapped
in - the assignment only specifies one sample user, and the engine's
behavior shouldn't depend on a specific id existing (see README)."""

USER = {
    "id": "user_101",
    "name": "Aarav Sharma",
    "language": "en",
    "subscription": "premium",
    "tonePreference": "motivational",
    "birthDetails": {
        "date": "1997-08-15",
        "time": "09:35",
        "place": "Delhi",
    },
}

KUNDLI = {
    "lagna": "Libra",
    "moonSign": "Scorpio",
    "currentDasha": {
        "mahadasha": "Rahu",
        "antardasha": "Mars",
    },
    "houses": {
        "6": {"lord": "Jupiter", "strength": "Average"},
        "7": {"lord": "Mars", "strength": "Weak"},
        "10": {"lord": "Moon", "strength": "Strong"},
    },
}

HOROSCOPE = {
    "career": "Networking may bring new opportunities.",
    "finance": "Avoid risky investments.",
    "health": "Prioritize proper sleep.",
    "relationship": "Communication with your partner improves.",
}

PANCHANG = {
    "date": "2026-08-01",
    "tithi": "Shukla Panchami",
    "nakshatra": "Rohini",
    "yoga": "Siddhi",
    "karana": "Bava",
}
