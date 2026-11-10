"""Load the flight history and join each flight to the weather at departure."""
import pandas as pd

from app.config import HISTORY_CSV, WEATHER_CSV
from app.data import generate


def ensure_data() -> None:
    """Generate sample data the first time the project runs."""
    if not HISTORY_CSV.exists() or not WEATHER_CSV.exists():
        generate.main()


def load_training_frame() -> pd.DataFrame:
    """Completed (non-cancelled) flights with their departure-hour weather."""
    ensure_data()
    flights = pd.read_csv(HISTORY_CSV)
    weather = pd.read_csv(WEATHER_CSV)
    flights = flights[flights["CANCELLED"] == 0].dropna(subset=["DEP_DEL15"]).copy()
    flights["HOUR"] = (flights["CRS_DEP_TIME"] // 100).astype(int)
    flights = flights.merge(weather, left_on=["FL_DATE", "HOUR"], right_on=["DATE", "HOUR"], how="inner")
    return flights.drop(columns=["DATE"])
