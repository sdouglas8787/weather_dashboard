# Weather Dashboard

A Python-based weather data pipeline that fetches, processes, and prepares hourly weather data for Power BI visualization.

## Features

- **Hourly granularity**: Preserves full time-of-day weather patterns
- **Auto-fill**: Automatically detects and fetches missing dates
- **Versioned forecasts**: Track forecast accuracy over time
- **Deduplication**: Safe to re-run - no duplicates created
- **Power BI ready**: Cleaned CSV files with helper columns

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Open the notebook
jupyter notebook notebooks/03_data_pipeline.ipynb

# 3. Run the cells:
# Cell 1: Fetch today's 7-day forecast
# Cell 2: Fetch historical actuals (with auto-fill)
# Cell 3: Process & clean to hourly files
```

## Data Flow

```
Cell 1 → data/raw/weather_forecast_YYYY-MM-DD.csv (hourly forecast)
Cell 2 → data/raw/weather_historical_START_to_END.csv (hourly actuals)
Cell 3 → Processes → data/processed/ (cleaned hourly data for Power BI)
         - weather_history_hourly.csv
         - weather_forecasts_hourly.csv
```

## Directory Structure

```
weather-dashboard/
├── data/
│   ├── raw/                        # Raw API data (backup/audit)
│   │   ├── weather_forecast_*.csv  # Versioned forecasts (one per day)
│   │   └── weather_historical_*.csv # Historical actuals (by date range)
│   └── processed/                  # Cleaned hourly data for Power BI
│       ├── weather_history_hourly.csv
│       └── weather_forecasts_hourly.csv
├── src/
│   ├── config.py                   # Paths & location settings
│   ├── fetch_weather.py            # API fetching functions
│   └── clean_weather.py            # Processing & cleaning
├── notebooks/
│   └── 03_data_pipeline.ipynb      # Main workflow (3 cells)
├── README.md                       # This file
├── WORKFLOW.md                     # Detailed process documentation
└── requirements.txt                # Python dependencies
```

## Workflow

### Cell 1: Fetch Forecast
Fetches 7-day hourly weather forecast for all locations.

**Output**: `data/raw/weather_forecast_2025-12-30.csv`
- Each day creates a NEW versioned file (no overwrites)
- Enables forecast accuracy tracking

### Cell 2: Fetch Historical Actuals
Fetches actual historical hourly weather for any date range.

**Auto-fill mode** (recommended):
```python
fetch_historical(auto_fill=True)
```
- Automatically detects last date in processed file
- Fetches from (last_date + 1) to yesterday
- Skips if already up to date

**Manual mode**:
```python
# Specific date range
fetch_historical("2023-01-01", "2023-12-31")  # All of 2023
fetch_historical("2024-01-01", "2024-12-31")  # All of 2024

# Yesterday only (default)
fetch_historical()
```

**Output**: `data/raw/weather_historical_2023-01-01_to_2023-12-31.csv`

### Cell 3: Process & Clean
Processes all raw files into cleaned hourly format for Power BI.

**What it does**:
1. Loads all raw historical and forecast files
2. Deduplicates by (datetime, location)
3. Adds Power BI helper columns (hour, date, year, month, etc.)
4. Preserves full hourly granularity (24 records/day/location)

**Output**:
- `data/processed/weather_history_hourly.csv` - All actuals
- `data/processed/weather_forecasts_hourly.csv` - All forecasts

**Safe to re-run**: Automatically deduplicates, no duplicates created.

## Power BI Setup

1. **Get Data** → **Text/CSV**
2. Navigate to: `data/processed/`
3. Select `weather_history_hourly.csv`

### Available Columns (28 total)

**Basic Weather Data:**
- `datetime`, `temperature_2m`, `relative_humidity_2m`, `location`, `country`

**Time Dimensions:**
- `hour` (0-23), `date`, `year`, `month`, `month_name`, `day_of_week`

**Calculated Columns for Data Science:**

| Category | Columns | Description |
|----------|---------|-------------|
| **Hourly Patterns** | `avg_temp_for_hour`<br>`min_temp_for_hour`<br>`max_temp_for_hour` | Typical temp for this hour across all dates<br>(e.g., "3 PM is usually 6.7°C") |
| **Daily Statistics** | `min_temp_day`<br>`max_temp_day`<br>`avg_temp_day` | Min, max, avg for this specific day<br>(all 24 hours have same values) |
| **Temperature Trends** | `temp_24hour_rolling_avg`<br>`temp_7day_rolling_avg`<br>`temp_30day_rolling_avg` | Rolling averages to smooth out noise<br>and identify trends |
| **Humidity Trends** | `humidity_24hour_rolling_avg`<br>`humidity_7day_rolling_avg` | Rolling humidity averages |
| **Temperature Changes** | `temp_change_1hour`<br>`temp_change_24hour` | Hour-over-hour change<br>Day-over-day change (same hour) |

**Full documentation:** See [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

### Power BI Analysis Examples

**Hourly Pattern Heatmap:**
```dax
Rows: hour (0-23)
Columns: location
Values: AVERAGE(avg_temp_for_hour)
// Shows typical temperature by hour of day
```

**Above/Below Trend:**
```dax
Temp vs 7-Day Avg = [temperature_2m] - [temp_7day_rolling_avg]
// Positive = warming trend, Negative = cooling trend
```

**Daily Temperature Range:**
```dax
Daily Range = [max_temp_day] - [min_temp_day]
// Shows temperature volatility
```

**Rapid Change Detection:**
```dax
Rapid Change = IF(ABS([temp_change_1hour]) > 2, "Alert", "Normal")
// Identifies sudden temperature shifts
```

## Configuration

Edit `src/config.py` to add/modify locations:

```python
LOCATIONS = [
    {
        "name": "London",
        "country": "UK",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London"
    },
    # Add more locations here
]
```

## Common Workflows

### Initial Setup (Backfill Years)
```python
# Cell 2: Fetch multiple years
fetch_historical("2023-01-01", "2023-12-31")
fetch_historical("2024-01-01", "2024-12-31")
fetch_historical("2025-01-01", "2025-12-29")

# Cell 3: Process all at once
```

### Daily Update
```python
# Cell 1: Today's forecast
fetch_forecast(save_versioned=True)

# Cell 2: Auto-fill missing dates
fetch_historical(auto_fill=True)

# Cell 3: Process both
```

## Why Hourly (Not Daily)?

For weather data, hourly granularity is essential:
- ✅ See temperature variation throughout the day
- ✅ Identify patterns by hour (morning chill, afternoon warmth)
- ✅ Power BI can aggregate to daily/weekly as needed
- ✅ Preserves all detail - can always aggregate up, never down
- ✅ Enables time-of-day analysis and visualizations

## Data Guarantees

### No Duplication
- ✅ Safe to re-fetch same date ranges
- ✅ Safe to re-run Cell 3 multiple times
- ✅ Deduplicates by (datetime, location) for actuals
- ✅ Deduplicates by (run_date, datetime, location) for forecasts

### Backup & Audit
- ✅ Raw files in `data/raw/` serve as backup
- ✅ Versioned forecasts track predictions over time
- ✅ Can recreate processed files anytime from raw

### Data Integrity
- ✅ Timezone-aware (uses location timezone)
- ✅ Every hour preserved (24 records/day/location)
- ✅ Forecast versioning enables accuracy analysis

## Troubleshooting

**"No historical files found"**
- Run Cell 2 first to fetch historical data

**"No forecast files found"**
- Run Cell 1 first to fetch forecast

**Data not updating in Power BI**
- Click Refresh in Power BI Desktop
- Verify processed files have recent timestamps

**Start fresh**
```bash
# Delete processed (keeps raw backups)
rm data/processed/*.csv

# Re-run Cell 3 to rebuild
```

## Data Sources

- **API**: [Open-Meteo](https://open-meteo.com/)
- **Forecast endpoint**: `api.open-meteo.com/v1/forecast`
- **Historical endpoint**: `archive-api.open-meteo.com/v1/archive`
- **License**: Open-Meteo data is free for non-commercial use

## Requirements

- Python 3.12+
- pandas
- requests
- jupyter (for notebook)

See `requirements.txt` for full dependencies.

## Documentation

- `README.md` (this file) - Quick start & overview
- `WORKFLOW.md` - Detailed process flow
- `FAQ.md` - Common questions & answers
- Notebook has inline documentation

## License

MIT License - see project repository for details
