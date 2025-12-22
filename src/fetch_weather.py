import pandas as pd
import requests
from datetime import datetime

from config import LOCATIONS, RAW_PATH, OPENMETEO_URL, HOURLY_VARIABLES


def fetch_location(location: dict[str, str | float]) -> pd.DataFrame:
    """Fetch weather data for a single location from Open-Meteo API."""
    params: dict[str, str | float] = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": location["timezone"],
    }

    response = requests.get(OPENMETEO_URL, params=params)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame({
        "datetime": data["hourly"]["time"],
        **{var: data["hourly"][var] for var in HOURLY_VARIABLES}
    })

    df["location"] = location["name"]
    df["country"] = location["country"]

    return df


def main():
    """Fetch weather for all locations and save to raw."""
    
    # Ensure output folder exists
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    
    # Fetch all locations
    all_data = []
    
    for location in LOCATIONS:
        print(f"Fetching: {location['name']}, {location['country']}")
        df = fetch_location(location)
        all_data.append(df) # type: ignore[call-overload]
    
    # Combine all locations
    combined = pd.concat(all_data, ignore_index=True) # type: ignore[call-overload]
    
    # Add metadata
    combined["run_date"] = datetime.today().date()
    combined["run_timestamp"] = datetime.now()
    
    # Save raw data (overwrites each run)
    output_file = RAW_PATH / "weather_live.csv"
    combined.to_csv(output_file, index=False)
    
    print(f"Raw weather data saved: {combined.shape}")
    print(f"Locations: {combined['location'].unique().tolist()}")
    print(f"Date range: {combined['datetime'].min()} to {combined['datetime'].max()}")
    
    return combined


if __name__ == "__main__":
    main()