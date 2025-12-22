import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import datetime
from pathlib import Path

# -----------------------------
# Setup API client
# -----------------------------
cache_session = requests_cache.CachedSession(
    ".cache", expire_after=3600
)
retry_session = retry(
    cache_session, retries=5, backoff_factor=0.2
)

openmeteo = openmeteo_requests.Client(session=retry_session)

# -----------------------------
# API request
# -----------------------------
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": 51.5074,      # London
    "longitude": -0.1278,
    "hourly": "temperature_2m,relative_humidity_2m",
    "timezone": "Europe/London"
}

responses = openmeteo.weather_api(url, params=params)
response = responses[0]

# -----------------------------
# Extract hourly data
# -----------------------------
hourly = response.Hourly()

temperature = hourly.Variables(0).ValuesAsNumpy()
humidity = hourly.Variables(1).ValuesAsNumpy()

dates = pd.date_range(
    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
    freq=pd.Timedelta(seconds=hourly.Interval()),
    inclusive="left"
)

df = pd.DataFrame({
    "datetime": dates,
    "temperature_c": temperature,
    "humidity_pct": humidity
})

df["run_date"] = datetime.today().date()

# -----------------------------
# Save raw data
# -----------------------------
output_path = Path("data/raw")
output_path.mkdir(parents=True, exist_ok=True)

df.to_csv(
    output_path / "weather_live.csv",
    index=False
)

if __name__ == "__main__":
    print("Raw weather data saved:", df.shape)

