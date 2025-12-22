import pandas as pd
from datetime import datetime

# Import settings from config
from config import RAW_PATH, PROCESSED_PATH


def load_raw_data() -> pd.DataFrame:
    """Load the raw weather data."""
    raw_file = RAW_PATH / "weather_live.csv"
    
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw data not found: {raw_file}")
    
    df: pd.DataFrame = pd.read_csv(raw_file, parse_dates=["datetime"])  # type: ignore[call-overload]
    return df


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly data to daily, grouped by location."""
    
    df = df.copy()
    df["date"] = df["datetime"].dt.date  # type: ignore[union-attr]
    
    daily = (
        df
        .groupby(["date", "location", "country"])  # type: ignore[union-attr]
        .agg(
            avg_temp_c=("temperature_2m", "mean"),
            min_temp_c=("temperature_2m", "min"),
            max_temp_c=("temperature_2m", "max"),
            avg_humidity_pct=("relative_humidity_2m", "mean"),
        )
        .reset_index()
    )
    
    daily["date"] = pd.to_datetime(daily["date"])  # type: ignore[arg-type]
    
    return daily


def append_to_history(new_data: pd.DataFrame) -> pd.DataFrame:
    """
    Append new data to history file, removing duplicates.
    Keeps all historical data - no overwrites.
    """
    
    # Ensure folder exists
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    
    history_file = PROCESSED_PATH / "weather_history.csv"
    
    if history_file.exists():
        existing: pd.DataFrame = pd.read_csv(history_file, parse_dates=["date"])  # type: ignore[call-overload]
        
        # Combine and remove duplicates (keep latest if same date+location)
        combined = pd.concat([existing, new_data], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["date", "location"], 
            keep="last"
        )
    else:
        combined = new_data
    
    # Sort by location then date
    combined = combined.sort_values(["location", "date"])
    
    # Add rolling 7-day average per location
    combined["temp_7d_avg"] = (
        combined
        .groupby("location")["avg_temp_c"]  # type: ignore[union-attr]
        .transform(lambda x: x.rolling(7, min_periods=1).mean())
    )
    
    # Add useful columns for Power BI filtering
    combined["year"] = combined["date"].dt.year  # type: ignore[union-attr]
    combined["month"] = combined["date"].dt.month  # type: ignore[union-attr]
    combined["month_name"] = combined["date"].dt.strftime("%B")  # type: ignore[union-attr]
    combined["day_of_week"] = combined["date"].dt.strftime("%A")  # type: ignore[union-attr]
    
    # Add processing timestamp
    combined["last_updated"] = datetime.now()
    
    # Save
    combined.to_csv(history_file, index=False)
    
    return combined


def main():
    """Main processing pipeline."""
    
    # Load raw
    raw = load_raw_data()
    print(f"  Loaded {len(raw)} hourly records")
    
    # Aggregate to daily
    daily = aggregate_daily(raw)
    print(f"  Aggregated to {len(daily)} daily records")
    
    # Append to history
    history = append_to_history(daily)
    print(f"  History now has {len(history)} total records")


if __name__ == "__main__":
    main()