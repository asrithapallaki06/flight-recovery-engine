"""Reproduce the README results: run ten ground-stop scenarios through every strategy.

Usage (from the repo root):
    cd backend && python ../scripts/benchmark.py

Prints a results table and saves docs/results.png.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.recovery.simulate import run  # noqa: E402

# (ground stop start, end, reserve crews): 2 to 5 hour stops, 0 to 8 reserves.
SCENARIOS = [
    (14, 17, 6), (13, 18, 6), (15, 17, 4), (14, 17, 0), (12, 17, 3),
    (16, 19, 6), (13, 16, 4), (15, 19, 8), (11, 14, 4), (17, 20, 6),
]


def main() -> dict:
    totals = {"No reassignment": 0, "Greedy": 0, "Optimizer": 0, "Optimizer + delay model": 0}
    print(f"{'Ground stop':<14}{'Res':>4}{'Hold':>7}{'Greedy':>8}{'Opt':>6}{'Opt+model':>11}")
    for start, end, reserves in SCENARIOS:
        with_model = run(start * 60, end * 60, reserves, use_risk=True)["strategies"]
        without = run(start * 60, end * 60, reserves, use_risk=False)["strategies"]
        row = [with_model["original"], with_model["greedy"], without["optimized"], with_model["optimized"]]
        counts = [s["metrics"]["cancelled"] for s in row]
        for name, n in zip(totals, counts):
            totals[name] += n
        print(f"{start:02d}:00-{end:02d}:00   {reserves:>4}{counts[0]:>7}{counts[1]:>8}{counts[2]:>6}{counts[3]:>11}")
    base = totals["No reassignment"]
    print("\nTotal cancellations")
    for name, n in totals.items():
        print(f"  {name:<26}{n:>4}   {round(100 * (base - n) / base)}% fewer than no reassignment")
    save_chart(totals)
    return totals


def save_chart(totals: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(totals)[::-1]
    values = [totals[n] for n in names]
    colors = ["#5cb8ff", "#3d7fb3", "#d6a03f", "#7d8894"]
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=150)
    fig.patch.set_facecolor("#10141a")
    ax.set_facecolor("#10141a")
    bars = ax.barh(names, values, color=colors, height=0.6)
    for bar, v in zip(bars, values):
        ax.text(v + 2, bar.get_y() + bar.get_height() / 2, str(v), va="center",
                color="#e6ebf0", fontsize=11, fontweight="bold")
    ax.set_xlim(0, max(values) * 1.15)
    ax.set_title("Flights cancelled across 10 ground-stop scenarios", color="#e6ebf0",
                 fontsize=12, loc="left", pad=12)
    ax.tick_params(colors="#8794a2", labelsize=10, length=0)
    ax.xaxis.set_visible(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    out = ROOT / "docs" / "results.png"
    fig.savefig(out, facecolor=fig.get_facecolor())
    print(f"\nSaved chart to {out}")


if __name__ == "__main__":
    main()
