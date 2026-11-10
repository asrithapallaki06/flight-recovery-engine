"""Download REAL flight and weather data to replace the generated sample data.

Flights: U.S. DOT Bureau of Transportation Statistics, On-Time Performance (monthly zips).
Weather: hourly Atlanta weather from the Open-Meteo historical API (free, no key).
         Times are requested in Atlanta local time, matching BTS scheduled times.

Usage, from the repo root on your own computer:
    pip install truststore        # use your computer's trusted certificates (recommended)
    python scripts/download_bts.py --year 2025 --months 6 7 8

If downloads still fail (some campus or work networks block them), download the
files in your browser instead and point the script at them:
    python scripts/download_bts.py --year 2025 --months 6 7 8 --local-dir ~/Downloads/bts

Then retrain:
    cd backend && python -m app.predictor.train
"""
import argparse
import calendar
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

# Use the operating system's trusted certificates when the truststore package is
# installed. This matches what your browser trusts (including networks that use
# their own certificates) and keeps certificate checks fully on.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "backend" / "datasets"
BTS_URL = ("https://transtats.bts.gov/PREZIP/"
           "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip")
WEATHER_URLS = [
    "https://archive-api.open-meteo.com/v1/archive",
    "https://api.open-meteo.com/v1/archive",
]
ATL_LAT, ATL_LON = 33.6407, -84.4277
THUNDERSTORM_CODES = {95, 96, 99}   # WMO weather codes for thunderstorms

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


def fetch(url: str, attempts: int = 3, timeout: int = 300) -> bytes:
    """Download a URL, retrying a couple of times because government sites can be slow."""
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "flight-recovery-engine"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - report any network failure clearly
            if attempt == attempts:
                raise RuntimeError(f"Could not download {url}: {exc}") from exc
            print(f"  attempt {attempt} failed ({exc}); retrying in 5s")
            time.sleep(5)


def clean_bts(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep ATL departures and convert BTS columns to the project's format."""
    df = raw[list(COLUMNS)].rename(columns=COLUMNS)
    df = df[df["ORIGIN"] == "ATL"].copy()
    # BTS has used both "2025-06-01" and "6/1/2025 12:00:00 AM" over the years.
    df["FL_DATE"] = pd.to_datetime(df["FL_DATE"], format="mixed").dt.strftime("%Y-%m-%d")
    for col in ["CRS_DEP_TIME", "CRS_ARR_TIME", "OP_CARRIER_FL_NUM", "CANCELLED"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["CRS_DEP_TIME"] = df["CRS_DEP_TIME"].replace(2400, 2359)   # midnight edge case
    return df.reset_index(drop=True)


def download_month(year: int, month: int, local_dir: Path | None = None) -> pd.DataFrame:
    url = BTS_URL.format(year=year, month=month)
    if local_dir:
        path = local_dir / Path(url).name
        if not path.exists():
            raise SystemExit(f"Missing {path}\nDownload it in your browser from:\n  {url}")
        print(f"Flights {year}-{month:02d}: reading {path.name}")
        archive = zipfile.ZipFile(path)
    else:
        print(f"Flights {year}-{month:02d}: downloading (about 30-60 MB)...")
        archive = zipfile.ZipFile(io.BytesIO(fetch(url)))
    csv_name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
    raw = pd.read_csv(archive.open(csv_name), usecols=list(COLUMNS), low_memory=False)
    df = clean_bts(raw)
    print(f"  kept {len(df):,} ATL departures")
    return df


def weather_from_open_meteo(payload: dict) -> pd.DataFrame:
    """Convert an Open-Meteo hourly response into the project's weather format."""
    h = payload["hourly"]
    times = pd.to_datetime(pd.Series(h["time"]))
    precip = pd.Series(h["precipitation"], dtype="float").fillna(0)
    codes = pd.Series(h["weather_code"], dtype="float").fillna(0).astype(int)
    thunder = codes.isin(THUNDERSTORM_CODES).astype(int)
    return pd.DataFrame({
        "DATE": times.dt.strftime("%Y-%m-%d"),
        "HOUR": times.dt.hour,
        "TEMP_F": pd.Series(h["temperature_2m"], dtype="float").round(1),
        "PRECIP_IN": precip.round(2),
        "WIND_KT": pd.Series(h["wind_speed_10m"], dtype="float").fillna(0).round(1),
        # The historical API has no visibility, so estimate it from rain and storms.
        "VIS_MI": [2.0 if t else 4.0 if p > 0.1 else 10.0 for t, p in zip(thunder, precip)],
        "THUNDER": thunder,
    })


def weather_query(year: int, months: list[int]) -> str:
    start = f"{year}-{min(months):02d}-01"
    last = max(months)
    end = f"{year}-{last:02d}-{calendar.monthrange(year, last)[1]:02d}"
    return (f"?latitude={ATL_LAT}&longitude={ATL_LON}&start_date={start}&end_date={end}"
            "&hourly=temperature_2m,precipitation,wind_speed_10m,weather_code"
            "&timezone=America%2FNew_York&temperature_unit=fahrenheit"
            "&wind_speed_unit=kn&precipitation_unit=inch")


def download_weather(year: int, months: list[int], local_dir: Path | None = None) -> pd.DataFrame:
    params = weather_query(year, months)
    if local_dir:
        path = local_dir / "weather.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}\nOpen this link in your browser and save the page as weather.json:\n"
                             f"  {WEATHER_URLS[0]}{params}")
        print(f"Weather: reading {path.name}")
        return weather_from_open_meteo(json.loads(path.read_text()))
    print("Weather: downloading...")
    last_error = None
    for base in WEATHER_URLS:
        try:
            payload = json.loads(fetch(base + params, timeout=120))
            if "hourly" in payload:
                return weather_from_open_meteo(payload)
            last_error = payload.get("reason", payload)
        except RuntimeError as exc:
            last_error = exc
    raise RuntimeError(f"Weather download failed: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="+", required=True, help="e.g. 6 7 8")
    parser.add_argument("--local-dir", type=Path, help="folder of files you downloaded in a browser")
    parser.add_argument("--print-links", action="store_true", help="print the download links and stop")
    args = parser.parse_args()

    if args.print_links:
        for m in args.months:
            print(BTS_URL.format(year=args.year, month=m))
        print(WEATHER_URLS[0] + weather_query(args.year, args.months) + "   (save as weather.json)")
        return

    local = args.local_dir.expanduser() if args.local_dir else None
    flights = pd.concat([download_month(args.year, m, local) for m in args.months], ignore_index=True)
    weather = download_weather(args.year, args.months, local)

    matched = flights.assign(HOUR=flights["CRS_DEP_TIME"] // 100).merge(
        weather, left_on=["FL_DATE", "HOUR"], right_on=["DATE", "HOUR"], how="inner")
    if len(matched) < 0.9 * len(flights):
        raise RuntimeError("Fewer than 90% of flights matched an hour of weather. Check the dates.")

    DATASETS.mkdir(parents=True, exist_ok=True)
    flights.to_csv(DATASETS / "flights_history.csv", index=False)
    weather.to_csv(DATASETS / "weather_history.csv", index=False)
    (DATASETS / "SOURCE.txt").write_text(
        f"real: BTS On-Time Performance {args.year} months {args.months}; Open-Meteo hourly weather\n")
    print(f"\nSaved {len(flights):,} ATL departures and {len(weather):,} weather hours.")
    print(f"Delay rate: {flights['DEP_DEL15'].mean():.1%}  Cancelled: {flights['CANCELLED'].mean():.1%}")
    print("Next: cd backend && python -m app.predictor.train")


if __name__ == "__main__":
    main()
