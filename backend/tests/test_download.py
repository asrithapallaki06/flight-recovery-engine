"""Tests for the real-data download script, using small samples shaped like the real files.

The real downloads need the internet, so these check the cleaning logic offline.
"""
import importlib.util
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "download_bts.py"
spec = importlib.util.spec_from_file_location("download_bts", SCRIPT)
download_bts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download_bts)


def bts_sample(date_value):
    """Two rows in BTS's raw column format: one ATL departure, one from another airport."""
    return pd.DataFrame({
        "FlightDate": [date_value, date_value],
        "Reporting_Airline": ["DL", "AA"],
        "Flight_Number_Reporting_Airline": [1234, 99],
        "Origin": ["ATL", "DFW"],
        "Dest": ["MCO", "ATL"],
        "CRSDepTime": [2400, 1015],
        "CRSArrTime": [130, 1330],
        "CRSElapsedTime": [91.0, 135.0],
        "Distance": [403.0, 731.0],
        "DepDelay": [-3.0, 22.0],
        "DepDel15": [0.0, 1.0],
        "Cancelled": [0.0, 0.0],
    })


def test_clean_bts_keeps_only_atl_departures_in_project_format():
    df = download_bts.clean_bts(bts_sample("2025-06-01"))
    assert len(df) == 1
    row = df.iloc[0]
    assert row["ORIGIN"] == "ATL" and row["DEST"] == "MCO" and row["OP_CARRIER"] == "DL"
    assert row["FL_DATE"] == "2025-06-01"
    assert row["CRS_DEP_TIME"] == 2359            # 2400 (midnight) is moved to 23:59


def test_clean_bts_handles_the_older_date_format():
    df = download_bts.clean_bts(bts_sample("6/1/2025 12:00:00 AM"))
    assert df.iloc[0]["FL_DATE"] == "2025-06-01"


def test_open_meteo_response_becomes_hourly_weather():
    payload = {"hourly": {
        "time": ["2025-06-01T00:00", "2025-06-01T15:00", "2025-06-01T16:00"],
        "temperature_2m": [74.1, 91.3, 85.0],
        "precipitation": [0.0, 0.62, 0.15],
        "wind_speed_10m": [5.2, 24.0, None],
        "weather_code": [0, 95, 61],
    }}
    wx = download_bts.weather_from_open_meteo(payload)
    assert list(wx["HOUR"]) == [0, 15, 16]
    assert list(wx["THUNDER"]) == [0, 1, 0]       # only code 95 is a thunderstorm
    assert list(wx["VIS_MI"]) == [10.0, 2.0, 4.0]
    assert wx["WIND_KT"].iloc[2] == 0             # missing wind becomes 0
    assert set(wx.columns) == {"DATE", "HOUR", "TEMP_F", "PRECIP_IN", "WIND_KT", "VIS_MI", "THUNDER"}


def test_downloaded_format_trains_the_model(tmp_path, monkeypatch):
    """Cleaned BTS + weather data must flow through the same feature builder as sample data."""
    from app.predictor.features import build_features

    flights = download_bts.clean_bts(bts_sample("2025-06-01"))
    flights["HOUR"] = flights["CRS_DEP_TIME"] // 100
    weather = download_bts.weather_from_open_meteo({"hourly": {
        "time": [f"2025-06-01T{h:02d}:00" for h in range(24)],
        "temperature_2m": [80.0] * 24, "precipitation": [0.0] * 24,
        "wind_speed_10m": [8.0] * 24, "weather_code": [0] * 24,
    }})
    joined = flights.merge(weather, left_on=["FL_DATE", "HOUR"], right_on=["DATE", "HOUR"])
    X, _ = build_features(joined)
    assert len(X) == 1 and "THUNDER" in X.columns
