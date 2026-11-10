"""Download REAL flight and weather data to replace the generated sample data.

Flights: U.S. DOT BTS On-Time Performance (monthly zip files).
Weather: hourly observations for ATL (station 72219) via the Meteostat library.

Usage (from the repo root, on your own computer):
    pip install meteostat
    python scripts/download_bts.py --year 2025 --months 6 7 8

It writes backend/datasets/flights_history.csv and weather_history.csv in the
same format the generator produces, then retrain with:
    cd backend && python -m app.predictor.train
"""
import argparse
import io
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "backend" / "datasets"
BTS_URL = ("https://transtats.bts.gov/PREZIP/"
           "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip")

# BTS column name -> the name this project uses.
COLUMNS = {
    "FlightDate": "FL_DATE",
    "Reporting_Airline": "OP_CARRIER",
    "Flight_Number_Reporting_Airline": "OP_CARRIER_FL_NUM",
    "Origin": "ORIGIN",
    "Dest": "DEST",
    "CRSDepTime": "CRS_DEP_TIME",
    "CRSArrTime": "CRS_ARR_TIME",
    "CRSElapsedTime": "CRS_ELAPSED_TIME",
    "Distance": "DISTANCE",
    "DepDelay": "DEP_DELAY",
    "DepDel15": "DEP_DEL15",
    "Cancelled": "CANCELLED",
}


def download_month(year: int, month: int) -> pd.DataFrame:
    url = BTS_URL.format(year=year, month=month)
    print(f"Downloading {url}")
    with urllib.request.urlopen(url, timeout=300) as resp:
        archive = zipfile.ZipFile(io.BytesIO(resp.read()))
    csv_name = next(n for n in archive.namelist() if n.endswith(".csv"))
    df = pd.read_csv(archive.open(csv_name), usecols=list(COLUMNS), low_memory=False)
    df = df.rename(columns=COLUMNS)
    return df[df["ORIGIN"] == "ATL"]


def download_weather(start: datetime, end: datetime) -> pd.DataFrame:
    try:
        from meteostat import Hourly
    except ImportError:
        sys.exit("Install the weather library first: pip install meteostat")
    wx = Hourly("72219", start, end).fetch().reset_index()   # 72219 = ATL
    return pd.DataFrame({
        "DATE": wx["time"].dt.strftime("%Y-%m-%d"),
        "HOUR": wx["time"].dt.hour,
        "TEMP_F": (wx["temp"] * 9 / 5 + 32).round(1),
        "PRECIP_IN": (wx["prcp"].fillna(0) / 25.4).round(2),
        "WIND_KT": (wx["wspd"].fillna(0) * 0.54).round(1),
        # Meteostat has no visibility; assume clear unless it's raining.
        "VIS_MI": wx["prcp"].fillna(0).apply(lambda p: 3.0 if p > 2 else 10.0),
        # Condition codes 25-27 are thunderstorms in Meteostat.
        "THUNDER": wx["coco"].fillna(0).between(25, 27).astype(int),
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", required=True)
    args = parser.parse_args()

    flights = pd.concat([download_month(args.year, m) for m in args.months], ignore_index=True)
    start = datetime(args.year, min(args.months), 1)
    end = datetime(args.year + (max(args.months) == 12), max(args.months) % 12 + 1, 1)
    weather = download_weather(start, end)

    DATASETS.mkdir(parents=True, exist_ok=True)
    flights.to_csv(DATASETS / "flights_history.csv", index=False)
    weather.to_csv(DATASETS / "weather_history.csv", index=False)
    print(f"Saved {len(flights):,} ATL departures and {len(weather):,} weather hours.")


if __name__ == "__main__":
    main()
