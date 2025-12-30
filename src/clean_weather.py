import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# Ensure we import from local config, not system config package
_src_dir = Path(__file__).parent.resolve()
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import config as _config
RAW_PATH = _config.RAW_PATH
PROCESSED_PATH = _config.PROCESSED_PATH


def load_raw_file(file_path: Path) -> pd.DataFrame:
    """Load a single raw weather data file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data not found: {file_path}")

    df: pd.DataFrame = pd.read_csv(file_path, parse_dates=["datetime"])  # type: ignore[call-overload]
    return df


def load_all_historical_files() -> pd.DataFrame:
    """Load all historical weather files from raw directory."""
    historical_files = list(RAW_PATH.glob("weather_historical_*.csv"))

    if not historical_files:
        raise FileNotFoundError(f"No historical files found in {RAW_PATH}")

    all_data = []
    for file in historical_files:
        print(f"  Loading: {file.name}")
        df = load_raw_file(file)
        all_data.append(df)

    combined = pd.concat(all_data, ignore_index=True)

    # Remove duplicates (keep last if same datetime+location)
    combined = combined.drop_duplicates(
        subset=["datetime", "location"],
        keep="last"
    )

    return combined


def aggregate_daily(df: pd.DataFrame, data_type: str = "actual") -> pd.DataFrame:
    """
    Aggregate hourly data to daily, grouped by location.

    Args:
        df: Hourly weather dataframe
        data_type: 'actual' or 'forecast' - used for metadata
    """

    df = df.copy()
    df["date"] = df["datetime"].dt.date  # type: ignore[union-attr]

    # Group by date + location
    groupby_cols = ["date", "location", "country"]

    # If we have run_date column, include it in groupby (for forecasts)
    if "run_date" in df.columns:
        groupby_cols.append("run_date")

    # Aggregation dictionary (exclude run_date since it's in groupby)
    agg_dict = {
        "avg_temp_c": ("temperature_2m", "mean"),
        "min_temp_c": ("temperature_2m", "min"),
        "max_temp_c": ("temperature_2m", "max"),
        "avg_humidity_pct": ("relative_humidity_2m", "mean"),
    }

    daily = (
        df
        .groupby(groupby_cols)  # type: ignore[union-attr]
        .agg(**agg_dict)
        .reset_index()
    )

    daily["date"] = pd.to_datetime(daily["date"])  # type: ignore[arg-type]
    daily["data_type"] = data_type

    return daily


def process_historical_hourly(start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    """
    Process historical actual weather data - KEEPS HOURLY GRANULARITY.
    Adds rich calculated columns for data science analysis.

    Args:
        start_date: Filter to dates >= this (YYYY-MM-DD)
        end_date: Filter to dates <= this (YYYY-MM-DD)
    """

    print("Processing historical actuals (hourly)...")

    # Load all historical files
    raw = load_all_historical_files()
    print(f"  Loaded {len(raw)} total hourly records")

    # Filter date range if specified
    if start_date or end_date:
        raw["date_only"] = pd.to_datetime(raw["datetime"]).dt.date  # type: ignore[union-attr]

        if start_date:
            raw = raw[raw["date_only"] >= pd.to_datetime(start_date).date()]  # type: ignore[union-attr]
            print(f"  Filtered to >= {start_date}")

        if end_date:
            raw = raw[raw["date_only"] <= pd.to_datetime(end_date).date()]  # type: ignore[union-attr]
            print(f"  Filtered to <= {end_date}")

        raw = raw.drop(columns=["date_only"])

    # Add basic time columns
    processed = raw.copy()
    processed["datetime"] = pd.to_datetime(processed["datetime"])  # type: ignore[arg-type]
    processed["date"] = processed["datetime"].dt.date  # type: ignore[union-attr]
    processed["hour"] = processed["datetime"].dt.hour  # type: ignore[union-attr]
    processed["year"] = processed["datetime"].dt.year  # type: ignore[union-attr]
    processed["month"] = processed["datetime"].dt.month  # type: ignore[union-attr]
    processed["month_name"] = processed["datetime"].dt.strftime("%B")  # type: ignore[union-attr]
    processed["day_of_week"] = processed["datetime"].dt.strftime("%A")  # type: ignore[union-attr]
    processed["data_type"] = "actual"

    # Sort by location and datetime for proper calculations
    processed = processed.sort_values(["location", "datetime"])

    print("  Adding calculated columns...")

    # === HOURLY STATISTICS (by hour of day, across all dates) ===
    # For each location + hour combination, calculate avg/min/max across all dates
    hourly_stats = (
        processed
        .groupby(["location", "hour"])["temperature_2m"]  # type: ignore[union-attr]
        .agg(
            avg_temp_for_hour="mean",
            min_temp_for_hour="min",
            max_temp_for_hour="max"
        )
        .reset_index()
    )
    processed = processed.merge(hourly_stats, on=["location", "hour"], how="left")

    # === DAILY STATISTICS (min/max temp for each day) ===
    # For each location + date, get the min and max temp of that day
    daily_stats = (
        processed
        .groupby(["location", "date"])["temperature_2m"]  # type: ignore[union-attr]
        .agg(
            min_temp_day="min",
            max_temp_day="max",
            avg_temp_day="mean"
        )
        .reset_index()
    )
    processed = processed.merge(daily_stats, on=["location", "date"], how="left")

    # === ROLLING AVERAGES (per location, ordered by datetime) ===
    # 7-day rolling average (168 hours)
    processed["temp_7day_rolling_avg"] = (
        processed
        .groupby("location")["temperature_2m"]  # type: ignore[union-attr]
        .transform(lambda x: x.rolling(window=168, min_periods=1).mean())
    )

    # 24-hour rolling average (1 day)
    processed["temp_24hour_rolling_avg"] = (
        processed
        .groupby("location")["temperature_2m"]  # type: ignore[union-attr]
        .transform(lambda x: x.rolling(window=24, min_periods=1).mean())
    )

    # 30-day rolling average (720 hours)
    processed["temp_30day_rolling_avg"] = (
        processed
        .groupby("location")["temperature_2m"]  # type: ignore[union-attr]
        .transform(lambda x: x.rolling(window=720, min_periods=1).mean())
    )

    # === HUMIDITY ROLLING AVERAGES ===
    processed["humidity_7day_rolling_avg"] = (
        processed
        .groupby("location")["relative_humidity_2m"]  # type: ignore[union-attr]
        .transform(lambda x: x.rolling(window=168, min_periods=1).mean())
    )

    processed["humidity_24hour_rolling_avg"] = (
        processed
        .groupby("location")["relative_humidity_2m"]  # type: ignore[union-attr]
        .transform(lambda x: x.rolling(window=24, min_periods=1).mean())
    )

    # === TEMPERATURE CHANGE ===
    # Hour-over-hour change
    processed["temp_change_1hour"] = (
        processed
        .groupby("location")["temperature_2m"]  # type: ignore[union-attr]
        .diff()
    )

    # Day-over-day change (compare same hour yesterday)
    processed["temp_change_24hour"] = (
        processed
        .groupby("location")["temperature_2m"]  # type: ignore[union-attr]
        .diff(periods=24)
    )

    # === ROUND ALL CALCULATED COLUMNS TO 3 DECIMAL PLACES ===
    # Makes the data easier to read and reduces file size
    calculated_columns = [
        "avg_temp_for_hour", "min_temp_for_hour", "max_temp_for_hour",
        "min_temp_day", "max_temp_day", "avg_temp_day",
        "temp_7day_rolling_avg", "temp_24hour_rolling_avg", "temp_30day_rolling_avg",
        "humidity_7day_rolling_avg", "humidity_24hour_rolling_avg",
        "temp_change_1hour", "temp_change_24hour"
    ]

    for col in calculated_columns:
        if col in processed.columns:
            processed[col] = processed[col].round(3)

    print(f"  Processed {len(processed)} hourly records with calculated columns")

    return processed


def process_historical(start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    """
    Process historical actual weather data.

    Args:
        start_date: Filter to dates >= this (YYYY-MM-DD)
        end_date: Filter to dates <= this (YYYY-MM-DD)
    """

    print("Processing historical actuals...")

    # Load all historical files
    raw = load_all_historical_files()
    print(f"  Loaded {len(raw)} total hourly records")

    # Filter date range if specified
    if start_date or end_date:
        raw["date_only"] = pd.to_datetime(raw["datetime"]).dt.date  # type: ignore[union-attr]

        if start_date:
            raw = raw[raw["date_only"] >= pd.to_datetime(start_date).date()]  # type: ignore[union-attr]
            print(f"  Filtered to >= {start_date}")

        if end_date:
            raw = raw[raw["date_only"] <= pd.to_datetime(end_date).date()]  # type: ignore[union-attr]
            print(f"  Filtered to <= {end_date}")

        raw = raw.drop(columns=["date_only"])

    # Aggregate to daily
    daily = aggregate_daily(raw, data_type="actual")
    print(f"  Aggregated to {len(daily)} daily records")

    return daily


def process_forecast(forecast_file: str | None = None) -> pd.DataFrame:
    """
    Process a forecast file.

    Args:
        forecast_file: Filename (e.g., 'weather_forecast_2025-12-30.csv')
                      If None, uses the most recent forecast file.
    """

    print("Processing forecast...")

    # Find forecast file
    if forecast_file is None:
        forecast_files = sorted(RAW_PATH.glob("weather_forecast_*.csv"), reverse=True)
        if not forecast_files:
            raise FileNotFoundError(f"No forecast files found in {RAW_PATH}")
        file_path = forecast_files[0]
        print(f"  Using most recent: {file_path.name}")
    else:
        file_path = RAW_PATH / forecast_file

    # Load and process
    raw = load_raw_file(file_path)
    print(f"  Loaded {len(raw)} hourly records")

    # Aggregate to daily
    daily = aggregate_daily(raw, data_type="forecast")
    print(f"  Aggregated to {len(daily)} daily records")

    return daily


def append_to_history(new_data: pd.DataFrame, history_type: str = "actuals", granularity: str = "daily") -> pd.DataFrame:
    """
    Append new data to history file, removing duplicates.

    Args:
        new_data: Data to append (daily or hourly)
        history_type: 'actuals' or 'forecasts' - determines output file
        granularity: 'daily' or 'hourly' - affects deduplication and filename
    """

    # Ensure folder exists
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

    # Determine output file based on type and granularity
    if history_type == "actuals":
        if granularity == "hourly":
            history_file = PROCESSED_PATH / "weather_history_hourly.csv"
        else:
            history_file = PROCESSED_PATH / "weather_history.csv"
    else:
        if granularity == "hourly":
            history_file = PROCESSED_PATH / "weather_forecasts_hourly.csv"
        else:
            history_file = PROCESSED_PATH / "weather_forecasts.csv"

    if history_file.exists():
        # Parse dates differently based on granularity
        if granularity == "hourly":
            existing: pd.DataFrame = pd.read_csv(history_file, parse_dates=["datetime"])  # type: ignore[call-overload]
        else:
            existing: pd.DataFrame = pd.read_csv(history_file, parse_dates=["date"])  # type: ignore[call-overload]

        # Combine and remove duplicates
        combined = pd.concat([existing, new_data], ignore_index=True)

        # Deduplication logic based on granularity
        if granularity == "hourly":
            # For hourly: (datetime, location) must be unique
            # For forecasts: (run_date, datetime, location) must be unique
            if history_type == "forecasts" and "run_date" in combined.columns:
                combined = combined.drop_duplicates(
                    subset=["run_date", "datetime", "location"],
                    keep="last"
                )
            else:
                combined = combined.drop_duplicates(
                    subset=["datetime", "location"],
                    keep="last"
                )
        else:
            # For daily: (date, location) must be unique
            # For forecasts: (run_date, date, location) must be unique
            if history_type == "forecasts" and "run_date" in combined.columns:
                combined = combined.drop_duplicates(
                    subset=["run_date", "date", "location"],
                    keep="last"
                )
            else:
                combined = combined.drop_duplicates(
                    subset=["date", "location"],
                    keep="last"
                )
    else:
        combined = new_data

    # Sort by location then date/datetime
    if granularity == "hourly":
        sort_cols = ["location", "datetime"]
        if "run_date" in combined.columns:
            sort_cols.insert(1, "run_date")
    else:
        sort_cols = ["location", "date"]
        if "run_date" in combined.columns:
            sort_cols.insert(1, "run_date")

    combined = combined.sort_values(sort_cols)

    # Add rolling 7-day average per location (for daily actuals only)
    if history_type == "actuals" and granularity == "daily":
        combined["temp_7d_avg"] = (
            combined
            .groupby("location")["avg_temp_c"]  # type: ignore[union-attr]
            .transform(lambda x: x.rolling(7, min_periods=1).mean())
        )

    # Add useful columns for Power BI filtering (if not already present)
    if granularity == "daily":
        if "year" not in combined.columns:
            combined["year"] = combined["date"].dt.year  # type: ignore[union-attr]
        if "month" not in combined.columns:
            combined["month"] = combined["date"].dt.month  # type: ignore[union-attr]
        if "month_name" not in combined.columns:
            combined["month_name"] = combined["date"].dt.strftime("%B")  # type: ignore[union-attr]
        if "day_of_week" not in combined.columns:
            combined["day_of_week"] = combined["date"].dt.strftime("%A")  # type: ignore[union-attr]
    # For hourly, these columns are already added in process_historical_hourly

    # Add processing timestamp
    combined["last_updated"] = datetime.now()

    # Save
    combined.to_csv(history_file, index=False)
    print(f"  Saved to: {history_file.name}")

    return combined


def main():
    """Main processing pipeline - processes all historical files as HOURLY."""

    print("\n=== Processing Historical Actuals (Hourly) ===")
    hourly_actuals = process_historical_hourly()
    history = append_to_history(hourly_actuals, history_type="actuals", granularity="hourly")
    print(f"  History now has {len(history)} total hourly records\n")


if __name__ == "__main__":
    main()