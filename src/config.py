from pathlib import Path

# -----------------------------
# Paths
# -----------------------------

# Get the project root directory (one level up from src/)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
RAW_PATH = (PROJECT_ROOT / "data" / "raw").resolve()
PROCESSED_PATH = (PROJECT_ROOT / "data" / "processed").resolve()

# -----------------------------
# Locations
# -----------------------------

# Add more locations as needed
# Find coordinates: https://www.latlong.net/

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
        "name": "Edinburgh",
        "country": "UK",
        "latitude": 55.9533,
        "longitude": -3.1883,
        "timezone": "Europe/London"
    },
    {
        "name": "Birmingham",
        "country": "UK",
        "latitude": 52.4862,
        "longitude": -1.8904,
        "timezone": "Europe/London"
    },
    {
        "name": "Cardiff",
        "country": "UK",
        "latitude": 51.4816,
        "longitude": -3.1791,
        "timezone": "Europe/London"
    },
]

# -----------------------------
# API Settings
# -----------------------------
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"

# Variables to fetch (hourly granularity)
# See full list: https://open-meteo.com/en/docs

HOURLY_VARIABLES = [
    # Temperature
    "temperature_2m",              # Actual temperature (°C)
    "apparent_temperature",        # Feels-like temperature (°C)
    "dewpoint_2m",                # Dew point (°C)

    # Humidity & Pressure
    "relative_humidity_2m",        # Relative humidity (%)
    "pressure_msl",               # Sea level pressure (hPa)

    # Precipitation
    "precipitation",              # Total precipitation (mm)
    "rain",                      # Rain only (mm)
    "snowfall",                  # Snowfall amount (cm)

    # Wind
    "windspeed_10m",             # Wind speed at 10m (km/h)
    "winddirection_10m",         # Wind direction (degrees)

    # Sky & Visibility
    "cloudcover",                # Cloud cover (%)
    "weathercode",               # WMO weather condition code
]

