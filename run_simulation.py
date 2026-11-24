#!/usr/bin/env python3
"""
run_simulation.py - one command that reproduces every result.

    python run_simulation.py            # 80-run main design + sensitivity + analysis + figures + dashboard
    python run_simulation.py --quick    # skip the sensitivity runs
    python run_simulation.py --workers 1

All outputs go to ./outputs/. Everything is Python model-based simulation
output, reproducible from the documented seed in sdwan_sim/config.py.
"""
import argparse, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sdwan_sim import experiment, analysis, figures, dashboard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "outputs"))
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--quick", action="store_true", help="skip sensitivity runs")
    a = ap.parse_args()
    t = time.time()
    os.makedirs(a.out, exist_ok=True)
    runs = experiment.run_main(a.out, a.workers)
    sens = None if a.quick else experiment.run_sensitivity(a.out, a.workers)
    tables = analysis.run_all(a.out, runs, sens)
    figs = figures.make_all(a.out, runs, sens)
    dashboard.build(a.out, runs, tables, figs)
    print(f"\nAll done in {time.time() - t:.0f} s. Open outputs/dashboard.html")


if __name__ == "__main__":
    main()
