from pathlib import Path

# -----------------------------
# Paths
# -----------------------------
RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")

# -----------------------------
# Locations
# -----------------------------
# Add more locations as needed
LOCATIONS: list[dict[str, str | float]] = [
    {
        "name": "London",
        "country": "UK",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London"
    },
    {
        "name": "Manchester",
        "country": "UK",
        "latitude": 53.4808,
        "longitude": -2.2426,
        "timezone": "Europe/London"
    },
        {
        "name": "Wokingham",
        "country": "UK",
        "latitude": 51.4112,
        "longitude": -0.83565,
        "timezone": "Europe/London"
    },
    {
        "name": "Edinburgh",
        "country": "UK",
        "latitude": 55.953251,
        "longitude": -3.188267,
        "timezone": "Europe/Edinburgh"
    },
]

# -----------------------------
# API Settings
# -----------------------------
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

# Variables to fetch
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
]