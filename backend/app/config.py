"""Shared settings for the whole backend.

Keeping every tunable number in one file makes the rules easy to find,
explain in an interview, and change in one place.
"""
from pathlib import Path

# Where generated CSVs and the trained model live.
DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
HISTORY_CSV = DATASETS_DIR / "flights_history.csv"
WEATHER_CSV = DATASETS_DIR / "weather_history.csv"
MODEL_PATH = DATASETS_DIR / "delay_model.json"
MODEL_META_PATH = DATASETS_DIR / "delay_model_meta.json"

HUB = "ATL"

# Spoke airports served from the hub, with block time in minutes.
# Block times are approximate, based on typical published schedules.
SPOKES = {
    "SAV": 55, "BNA": 65, "CLT": 70, "JAX": 70, "RDU": 85,
    "MCO": 90, "TPA": 90, "DCA": 110, "FLL": 110, "MIA": 115,
    "ORD": 120, "DTW": 120, "IAH": 135, "LGA": 135, "JFK": 140,
    "DFW": 150, "AUS": 155, "BOS": 155, "MSP": 160, "DEN": 210,
    "PHX": 250, "SLC": 270, "LAX": 285, "SFO": 300, "SEA": 330,
}

# Simplified crew legality rules (real FAA Part 117 rules are more detailed).
REPORT_MINUTES = 60        # crew reports this long before its first departure
MAX_DUTY_MINUTES = 780     # 13-hour maximum duty day, report to last arrival
MIN_TURN_MINUTES = 40      # minimum time between arriving and departing again

# Recovery settings.
MAX_DELAY_MINUTES = 240    # a flight delayed more than 4 hours is cancelled
BATCH_MINUTES = 60         # optimizer re-plans in 1-hour batches
