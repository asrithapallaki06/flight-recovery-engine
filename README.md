# vipr-mobile-cloud

Mobile/cloud data path for the VIPR: DRIVE pedestrian safety prototype.
Owner: Asritha · Started Oct 14, 2026

Phone telemetry → cloud API → (RSU dashboard reads `/latest`) → analytics logs.
Right now the "phone" is a simulator and the "cloud" is a local stand-in with the
same endpoints the Oracle service will have. **All data here is simulated** unless
`source` says otherwise.

## Files

| File | Stage | What it does |
|---|---|---|
| `schema.md` | 2 | Field-by-field contract for telemetry and alert records |
| `test_plan.md` | 2 | Delivery-rate test design and safety rules |
| `validate.py` | 2 | Checks records against the schema (`--demo` shows good/bad cases) |
| `telemetry_sender.py` | 3 | Simulated pedestrian at 1 Hz; file output, POST, real-time, replay |
| `plot_path.py` | 3 | True path vs. GPS fixes, and speed over time |
| `cloud_api.py` | 4 | FastAPI stand-in: `POST /telemetry`, `GET /latest`, `GET /health` |
| `check_stage4.py` | 4 | Sent vs. stored, transit time, stale-flag check |
| `logs/` | — | Raw `.jsonl` logs, ground-truth CSVs, plots |

## Setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux
pip install fastapi uvicorn matplotlib
```

## Run

Stages 2–3 (no server needed):
```
python validate.py --demo
python telemetry_sender.py --duration 300 --out logs/sim_run1.jsonl
python validate.py logs/sim_run1.jsonl
python plot_path.py logs/sim_run1.jsonl
```

Stage 4 (two terminals):
```
# terminal 1 - the cloud stand-in
uvicorn cloud_api:app --port 8000

# terminal 2 - 5 minutes of live telemetry, then the check
python telemetry_sender.py --duration 300 --url http://localhost:8000/telemetry --realtime --out logs/stage4_sent.jsonl
python check_stage4.py logs/stage4_sent.jsonl
```
Open http://localhost:8000/docs in a browser to see and try every endpoint.

Replay a recorded trace with its original timing:
```
python telemetry_sender.py --replay logs/sim_run1.jsonl --url http://localhost:8000/telemetry
```

## Configuration and credentials

| Variable | Default | Meaning |
|---|---|---|
| `VIPR_DB_PATH` | `telemetry.db` | SQLite file for the local stand-in |
| `VIPR_STALE_MS` | `2000` | Stale threshold (reasoning in `schema.md`) |

Oracle credentials go in environment variables or a `.env` file that is listed in
`.gitignore`. **Never commit credentials.** Moving to Oracle: replace `db()` in
`cloud_api.py` with an Oracle connection; endpoints and record format stay the same.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `ModuleNotFoundError: fastapi` | Virtual environment not active, or packages not installed |
| Sender prints `error: Connection refused` | API not running; start terminal 1 first |
| `422` with "must be ISO-8601 UTC ending in 'Z'" | Sender is using local time; timestamps must be UTC |
| `/latest` returns 404 | Wrong `session_id`; check `/health` record count |
| Data age jumps 0–1000 ms every second | Normal at 1 Hz: the newest record ages until the next one arrives |

## Rollback

Each stage is a separate commit. To go back: `git log` to find the commit, then
`git checkout <commit> -- <file>`. Delete `telemetry.db` to reset the stand-in database.

## Known limitations

- Simulated GPS noise is cleaner than real urban GPS (no building multipath).
- First record's heading is 0.0 (no previous point to compute it from).
- Localhost transit time (~2 ms) says nothing about real cellular delay; see Stage 5.
- Origin coordinate is a placeholder, not the test intersection.
