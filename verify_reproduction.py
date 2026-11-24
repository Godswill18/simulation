#!/usr/bin/env python3
"""
verify_reproduction.py - checks that your run reproduces the results reported
in the chapters (reference/run_level_results_reference.csv).

    python verify_reproduction.py
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ref = pd.read_csv(os.path.join(HERE, "reference", "run_level_results_reference.csv"))
new_path = os.path.join(HERE, "outputs", "data", "run_level_results.csv")
if not os.path.exists(new_path):
    sys.exit("No outputs yet: run RUN_SIMULATION.bat (or python run_simulation.py) first.")
new = pd.read_csv(new_path)
skip = {"wall_time_s"}
num = [c for c in ref.columns if c not in skip and pd.api.types.is_numeric_dtype(ref[c])]
ref, new = ref.set_index("run_id"), new.set_index("run_id")
if set(ref.index) != set(new.index):
    sys.exit("Different set of runs - was the design changed?")
new = new.loc[ref.index]
worst = []
for c in num:
    a, b = ref[c].astype(float).values, new[c].astype(float).values
    both_nan = np.isnan(a) & np.isnan(b)
    d = np.where(both_nan, 0.0, np.abs(a - b))
    rel = np.nanmax(d / np.maximum(np.abs(a), 1e-9)) if len(a) else 0
    worst.append((rel, c))
worst.sort(reverse=True)
print(f"Compared {len(ref)} runs x {len(num)} numeric columns with the reference results.")
if worst[0][0] == 0:
    print("IDENTICAL: your run reproduces the reported results exactly.")
elif worst[0][0] < 1e-3:
    print(f"MATCH: largest relative difference {worst[0][0]:.2e} ({worst[0][1]}), rounding level only.")
else:
    print("DIFFERENT: largest relative differences:")
    for r, c in worst[:8]:
        print(f"   {c:40s} {r:.3%}")
    print("Different numpy/pandas versions can change random streams slightly. Report the versions in "
          "outputs/run_manifest.json and use your own outputs consistently in the chapters.")
