import pandas as pd
import requests
from datetime import datetime, date, timedelta
import sys
from pathlib import Path

# Ensure we import from local config, not system config package
_src_dir = Path(__file__).parent.resolve()
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import config as _config
LOCATIONS = _config.LOCATIONS
RAW_PATH = _config.RAW_PATH
OPENMETEO_URL = _config.OPENMETEO_URL
OPENMETEO_HISTORICAL_URL = _config.OPENMETEO_HISTORICAL_URL
HOURLY_VARIABLES = _config.HOURLY_VARIABLES


def fetch_location_forecast(location: dict[str, str | float]) -> pd.DataFrame:
    """Fetch forecast data for a single location from Open-Meteo API."""
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


def fetch_location_historical(
    location: dict[str, str | float],
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """Fetch historical actual weather data for a single location."""
    params: dict[str, str | float] = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": location["timezone"],
    }

    response = requests.get(OPENMETEO_HISTORICAL_URL, params=params)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame({
        "datetime": data["hourly"]["time"],
        **{var: data["hourly"][var] for var in HOURLY_VARIABLES}
    })

    df["location"] = location["name"]
    df["country"] = location["country"]

    return df


def fetch_forecast(save_versioned: bool = True, verbose: bool = True) -> pd.DataFrame:
    """
    Fetch forecast for all locations and save to raw.

    Args:
        save_versioned: If True, saves with run_date prefix for tracking forecast versions.
                       If False, saves as weather_live.csv (overwrites).
    """

    # Ensure output folder exists
    RAW_PATH.mkdir(parents=True, exist_ok=True)

    # Fetch all locations
    all_data = []

    for location in LOCATIONS:
        print(f"Fetching forecast: {location['name']}, {location['country']}")
        df = fetch_location_forecast(location)
        all_data.append(df) # type: ignore[call-overload]

    # Combine all locations
    combined = pd.concat(all_data, ignore_index=True) # type: ignore[call-overload]

    # Add metadata
    run_date = datetime.today().date()
    combined["run_date"] = run_date
    combined["run_timestamp"] = datetime.now()
    combined["data_type"] = "forecast"

    # Save raw data
    if save_versioned:
        output_file = RAW_PATH / f"weather_forecast_{run_date}.csv"
        print(f"Saving versioned forecast: {output_file.name}")
    else:
        output_file = RAW_PATH / "weather_live.csv"
        print(f"Saving as weather_live.csv (overwrites previous)")

    combined.to_csv(output_file, index=False)

    print(f"Forecast data saved: {combined.shape}")
    print(f"Locations: {combined['location'].unique().tolist()}")
    print(f"Date range: {combined['datetime'].min()} to {combined['datetime'].max()}")

    return combined


def fetch_historical(start_date: str | None = None, end_date: str | None = None, auto_fill: bool = False) -> pd.DataFrame:
    """
    Fetch historical actual weather data for all locations.

    Args:
        start_date: Start date in YYYY-MM-DD format (default: yesterday)
        end_date: End date in YYYY-MM-DD format (default: yesterday)
        auto_fill: If True and start_date is None, finds last historical date and fetches from there to yesterday

    Examples:
        fetch_historical("2023-01-01", "2023-12-31")  # Get all of 2023
        fetch_historical("2024-01-01", "2024-12-31")  # Get all of 2024
        fetch_historical()  # Get yesterday's actuals
        fetch_historical(auto_fill=True)  # Get from last historical date to yesterday
    """

    # Auto-fill: find last historical date and fetch from there
    if auto_fill and start_date is None:
        PROCESSED_PATH = _config.PROCESSED_PATH
        import pandas as pd_auto

        last_date = None

        # Check PROCESSED folder first (preferred - has deduplication)
        history_file_hourly = PROCESSED_PATH / "weather_history_hourly.csv"
        history_file_daily = PROCESSED_PATH / "weather_history.csv"

        if history_file_hourly.exists():
            history = pd_auto.read_csv(history_file_hourly, parse_dates=["datetime"])
            last_date = history["datetime"].max().date()
            print(f"Auto-fill: Checking processed folder - last date: {last_date}")
        elif history_file_daily.exists():
            history = pd_auto.read_csv(history_file_daily, parse_dates=["date"])
            last_date = history["date"].max().date()
            print(f"Auto-fill: Checking processed folder - last date: {last_date}")

        # Also check RAW folder for safety (in case processed wasn't run yet)
        raw_files = sorted(RAW_PATH.glob("weather_historical_*.csv"))
        if raw_files:
            # Parse dates from filenames: weather_historical_START_to_END.csv
            raw_dates = []
            for f in raw_files:
                try:
                    # Extract end date from filename
                    parts = f.stem.split("_to_")
                    if len(parts) == 2:
                        end_date_str = parts[1]
                        raw_dates.append(pd_auto.to_datetime(end_date_str).date())
                except:
                    pass

            if raw_dates:
                raw_last_date = max(raw_dates)
                print(f"Auto-fill: Checking raw folder - last date: {raw_last_date}")

                # Use the most recent date from both sources
                if last_date is None or raw_last_date > last_date:
                    last_date = raw_last_date
                    print(f"Auto-fill: Using raw folder date as it's more recent")

        # If we found a last date, calculate what to fetch
        if last_date:
            next_date = last_date + timedelta(days=1)
            yesterday = date.today() - timedelta(days=1)

            if next_date <= yesterday:
                start_date = str(next_date)
                end_date = str(yesterday)
                print(f"Auto-fill: Fetching missing data from {start_date} to {end_date}")
            else:
                print(f"Auto-fill: Already up to date (last date: {last_date})")
                return pd.DataFrame()
        else:
            print("Auto-fill: No history files found, fetching yesterday")
            yesterday = date.today() - timedelta(days=1)
            start_date = str(yesterday)
            end_date = str(yesterday)

    # Default to yesterday if not specified
    if start_date is None or end_date is None:
        yesterday = date.today() - timedelta(days=1)
        start_date = start_date or str(yesterday)
        end_date = end_date or str(yesterday)

    # Safety: Validate and cap dates (historical API only has data up to yesterday)
    yesterday = date.today() - timedelta(days=1)

    # Validate date format and catch invalid dates (e.g., Nov 31st)
    try:
        start_date_obj = pd.to_datetime(start_date).date()
    except Exception as e:
        raise ValueError(
            f"Invalid start_date '{start_date}'. Must be a valid date in YYYY-MM-DD format.\n"
            f"Error: {str(e)}"
        )

    try:
        end_date_obj = pd.to_datetime(end_date).date()
    except Exception as e:
        raise ValueError(
            f"Invalid end_date '{end_date}'. Must be a valid date in YYYY-MM-DD format.\n"
            f"Common mistake: Nov has 30 days (not 31), Feb has 28/29 days.\n"
            f"Error: {str(e)}"
        )

    # Cap end_date at yesterday (can't fetch future data)
    if end_date_obj > yesterday:
        print(f"⚠ Warning: End date {end_date} is in the future.")
        print(f"  Adjusting to yesterday: {yesterday}")
        end_date = str(yesterday)
        end_date_obj = yesterday

    # Validate start_date isn't in the future
    if start_date_obj > yesterday:
        raise ValueError(
            f"Start date {start_date} is in the future. "
            f"Historical API only has data up to yesterday ({yesterday})."
        )

    # Ensure start_date <= end_date
    if start_date_obj > end_date_obj:
        raise ValueError(f"Start date {start_date} is after end date {end_date}.")

    # Ensure output folder exists
    RAW_PATH.mkdir(parents=True, exist_ok=True)

    # Fetch all locations
    all_data = []

    for location in LOCATIONS:
        print(f"Fetching historical: {location['name']}, {location['country']} ({start_date} to {end_date})")
        df = fetch_location_historical(location, start_date, end_date)
        all_data.append(df) # type: ignore[call-overload]

    # Combine all locations
    combined = pd.concat(all_data, ignore_index=True) # type: ignore[call-overload]

    # Add metadata
    combined["run_date"] = datetime.today().date()
    combined["run_timestamp"] = datetime.now()
    combined["data_type"] = "actual"

    # Save raw data with date range in filename
    output_file = RAW_PATH / f"weather_historical_{start_date}_to_{end_date}.csv"
    combined.to_csv(output_file, index=False)

    print(f"Historical data saved: {combined.shape}")
    print(f"Locations: {combined['location'].unique().tolist()}")
    print(f"Date range: {combined['datetime'].min()} to {combined['datetime'].max()}")

    return combined


def main():
    """Main function - fetch forecast with versioning by default."""
    return fetch_forecast(save_versioned=True)


if __name__ == "__main__":
    main()