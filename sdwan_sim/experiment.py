"""
experiment.py - the 80-run main design and the supplementary sensitivity runs.

MAIN DESIGN (Chapter 3, Section 3.6), 2 x 4 x 2 x 5 = 80 runs
  treatment   static | dps
  load        50, 150, 300, 450 tps per branch
  condition   steady-state (5 repetitions)
              impairment-event (5 repetitions: r1-r3 brownout P1, r4-r5 blackout P2)

Pairing: run (static, L, c, r) and run (dps, L, c, r) share one seed, so they
face the same arrivals and the same random draws (common random numbers).

Order: every run starts from a fresh model state, so run order cannot affect
results; randomising the order (needed on a physical testbed) is unnecessary.
"""
import dataclasses, json, os, platform, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from .config import SimConfig
from .run import simulate_run, run_id

REPRESENTATIVE = [(300, "brownout", 1), (300, "blackout", 4)]


def main_design(cfg):
    rows = []
    for tr in ("static", "dps"):
        for L in cfg.loads_tps:
            for r in range(1, cfg.reps_steady + 1):
                rows.append(dict(treatment=tr, load_tps=L, condition_group="steady-state",
                                 condition="steady", rep=r))
            for r, c in enumerate(cfg.impairment_split, start=1):
                rows.append(dict(treatment=tr, load_tps=L, condition_group="impairment-event",
                                 condition=c, rep=r))
    df = pd.DataFrame(rows)
    # impairment repetitions are numbered 1-5 inside their group; brownout = 1-3, blackout = 4-5
    df["run_id"] = [run_id(t, L, c, r) for t, L, c, r in zip(df.treatment, df.load_tps, df.condition, df.rep)]
    return df


SENSITIVITY = [
    # name, description, config overrides, treatments, conditions, loads
    ("S0_baseline", "Main-design parameters (reference for S1-S6, same seeds)",
     {}, ["static", "dps"], ["steady", "brownout", "blackout"], [300, 450]),
    ("S1_static_no_backup", "Static single path with no backup (original Chapter 3 baseline)",
     {"static_backup_enabled": False}, ["static"], ["brownout", "blackout"], [300]),
    ("S2_static_slow_detection", "Static failover detection 5 s probes x 3 misses",
     {"static_probe_interval_s": 5.0}, ["static"], ["blackout"], [300]),
    ("S3_policy_delay_1s", "1 s policy/route installation delay for both policies",
     {"policy_update_delay_s": 1.0}, ["static", "dps"], ["brownout", "blackout"], [300]),
    ("S4_timeout_2s", "Stricter 2 s transaction timeout (terminal-style)",
     {"timeout_s": 2.0}, ["static", "dps"], ["brownout", "blackout"], [300]),
    ("S5_dps_probe_window_10", "DPS latency/jitter window of 10 probes instead of 30",
     {"dps_latency_window": 10}, ["dps"], ["brownout"], [300]),
    ("S6_dps_holddown_20s", "DPS hold-down of 20 s before returning to Path A",
     {"dps_holddown_s": 20.0}, ["dps"], ["steady", "brownout"], [450]),
]
SENS_REPS = 5


def _job(args):
    cfg_dict, tr, L, c, r, keep = args
    cfg = SimConfig(**cfg_dict)
    return simulate_run(cfg, tr, L, c, r, keep_detail=keep)


def _cfg_kwargs(cfg):
    return {f.name: getattr(cfg, f.name) for f in dataclasses.fields(cfg)}


def run_jobs(jobs, workers):
    if workers <= 1:
        return [_job(j) for j in jobs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_job, jobs, chunksize=2))


def run_main(out_dir, workers=None, cfg=None, log=print):
    cfg = cfg or SimConfig()
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    data = os.path.join(out_dir, "data"); os.makedirs(data, exist_ok=True)
    design = main_design(cfg)
    design.to_csv(os.path.join(data, "experimental_design.csv"), index=False)
    cfg.save(os.path.join(out_dir, "parameters.json"))
    jobs = [(_cfg_kwargs(cfg), row.treatment, int(row.load_tps), row.condition, int(row.rep),
             (int(row.load_tps), row.condition, int(row.rep)) in REPRESENTATIVE)
            for row in design.itertuples()]
    t0 = time.time()
    log(f"Running {len(jobs)} main-design runs on {workers} worker(s) ...")
    res = run_jobs(jobs, workers)
    summaries, ts, ev = [], [], []
    for (s, t, e, d), row in zip(res, design.itertuples()):
        s["condition_group"] = row.condition_group
        summaries.append(s); ts.append(t); ev.extend(e)
        if d is not None:
            d["transactions"].to_csv(os.path.join(data, f"transactions_{s['run_id']}.csv.gz"), index=False)
            if d["monitor"] is not None:
                d["monitor"].round(4).to_csv(os.path.join(data, f"dps_monitor_branch1_{s['run_id']}.csv"), index=False)
    runs = pd.DataFrame(summaries)
    front = ["run_id", "cell_id", "treatment", "policy", "load_tps", "condition_group", "condition", "rep", "seed"]
    runs = runs[front + [c for c in runs.columns if c not in front]]
    runs.to_csv(os.path.join(data, "run_level_results.csv"), index=False)
    pd.concat(ts).to_csv(os.path.join(data, "timeseries_per_second.csv.gz"), index=False)
    pd.DataFrame(ev).to_csv(os.path.join(data, "path_switch_events.csv"), index=False)
    manifest = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": len(runs),
                "master_seed": cfg.master_seed, "runtime_s": round(time.time() - t0, 1),
                "python": sys.version.split()[0], "platform": platform.platform(),
                "numpy": np.__version__, "pandas": pd.__version__,
                "label": "Python model-based simulation results (not real-world measurements)"}
    json.dump(manifest, open(os.path.join(out_dir, "run_manifest.json"), "w"), indent=2)
    log(f"Main design done in {manifest['runtime_s']} s -> {data}")
    return runs


def run_sensitivity(out_dir, workers=None, log=print):
    base = SimConfig()
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    rows = []
    for name, desc, over, treats, conds, loads in SENSITIVITY:
        cfg = dataclasses.replace(base, **over)
        jobs, meta = [], []
        for tr in treats:
            for c in conds:
                for L in loads:
                    for r in range(1, SENS_REPS + 1):
                        jobs.append((_cfg_kwargs(cfg), tr, L, c, r, False))
                        meta.append((tr, c, r))
        for (s, _, _, _), (tr, c, r) in zip(run_jobs(jobs, workers), meta):
            s.update(scenario=name, scenario_description=desc, overrides=json.dumps(over))
            rows.append(s)
        log(f"  sensitivity {name}: {len(jobs)} runs")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "data", "sensitivity_results.csv"), index=False)
    return df
