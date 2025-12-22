import pandas as pd
from pathlib import Path
from datetime import date

# -----------------------------
# Paths
# -----------------------------
RAW_PATH = Path("data/raw/weather_live.csv")
PROCESSED_PATH = Path("data/processed")

# Ensure folders exist
(PROCESSED_PATH / "mtd").mkdir(parents=True, exist_ok=True)
(PROCESSED_PATH / "ytd").mkdir(parents=True, exist_ok=True)
(PROCESSED_PATH / "snapshots").mkdir(parents=True, exist_ok=True)

# -----------------------------
# Load raw data
# -----------------------------
df = pd.read_csv(RAW_PATH, parse_dates=["datetime"])

# -----------------------------
# Daily aggregation
# -----------------------------
daily = (
    df
    .set_index("datetime")
    .resample("D")
    .agg(
        avg_temp_c=("temperature_c", "mean"),
        avg_humidity_pct=("humidity_pct", "mean"),
        min_temp_c=("temperature_c", "min"),
        max_temp_c=("temperature_c", "max"),
    )
    .reset_index()
)

# -----------------------------
# Rolling features
# -----------------------------
daily["temp_7d_avg"] = daily["avg_temp_c"].rolling(7).mean()

# -----------------------------
# Save outputs
# -----------------------------
today = date.today()

daily.to_csv(
    PROCESSED_PATH / "mtd" / "weather_mtd.csv",
    index=False
)

daily.to_csv(
    PROCESSED_PATH / "ytd" / f"weather_ytd_{today.year}.csv",
    index=False
)

daily.to_csv(
    PROCESSED_PATH / "snapshots" / f"weather_{today}.csv",
    index=False
)

print("Processed weather data saved:", daily.shape)

