#!/usr/bin/env python3
"""
demo.py - live demonstration for the defence (about 2 seconds per scenario).

Runs ONE paired comparison: Static vs Dynamic Path Selection, same seed, same
traffic, same fault. Prints what each policy did and when, then shows a chart.

    python demo.py                               # brownout, 300 tps per branch
    python demo.py --condition blackout --load 150
    python demo.py --condition steady --load 450 # shows flapping at congested load
"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import matplotlib
from sdwan_sim.config import SimConfig
from sdwan_sim.run import simulate_run

LBL = {"static": "STATIC  ", "dps": "DYNAMIC "}
PATH = {0: "no path", 1: "Path A", 2: "Path B"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["steady", "brownout", "blackout"], default="brownout")
    ap.add_argument("--load", type=int, choices=[50, 150, 300, 450], default=300)
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args()
    cfg = SimConfig()
    print("=" * 78)
    print("PYTHON MODEL-BASED SIMULATION (not a measurement of any real bank network)")
    print(f"Scenario: {a.condition}, {a.load} tps per branch x {cfg.n_branches} branches, repetition {a.rep}")
    if a.condition != "steady":
        print(f"Fault on Path A of every branch at t = {cfg.fault_at_s:.0f} s for {cfg.fault_duration_s:.0f} s "
              f"(measurement time). Profile: {'P1 brownout 50+/-20 ms, 2 % loss' if a.condition == 'brownout' else 'P2 blackout, 100 % loss'}")
    print("=" * 78)
    res = {}
    for tr in ("static", "dps"):
        s, ts, ev, det = simulate_run(cfg, tr, a.load, a.condition, a.rep, keep_detail=True)
        res[tr] = (s, ts, ev)
        print(f"\n{LBL[tr]}path selection - switching events, branch 1 (time from start of measurement):")
        b1 = [e for e in ev if e["branch"] == 1 and e["t"] >= cfg.warmup_s]
        for e in b1[:8]:
            print(f"   t = {e['t'] - cfg.warmup_s:7.1f} s   {PATH[e['from']]} -> {PATH[e['to']]}")
        if len(b1) > 8:
            print(f"   ... {len(b1) - 8} more events (all branches: {s['path_switches']})")
        if not b1:
            print("   none - traffic stayed on Path A for the whole run")
    rows = [("Transactions attempted", "attempted", 0), ("Transaction availability (%)", "txn_availability_pct", 3),
            ("Mean response time (ms)", "rt_mean_ms", 1), ("p95 response time (ms)", "rt_p95_ms", 1),
            ("p99 response time (ms)", "rt_p99_ms", 1), ("Network latency, mean RTT (ms)", "net_rtt_mean_ms", 1),
            ("Message loss (%)", "msg_loss_pct", 3), ("Service availability (%)", "service_availability_pct", 3),
            ("SLA-compliant time (%)", "sla_compliant_time_pct", 2), ("Path switches (3 branches)", "path_switches", 0)]
    if a.condition != "steady":
        rows += [("Fault-window p95 RT (ms)", "fault_rt_p95_ms", 1),
                 ("Fault-window service availability (%)", "fault_service_availability_pct", 2),
                 ("Failover time (s)", "failover_time_s_median", 2), ("Fail-back time (s)", "failback_time_s_median", 2)]
    print(f"\n{'Metric':40s} {'Static':>14s} {'Dynamic':>14s}")
    print("-" * 70)
    for name, k, nd in rows:
        v = [res[t][0].get(k, np.nan) for t in ("static", "dps")]
        f = lambda x: "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{nd}f}"
        print(f"{name:40s} {f(v[0]):>14s} {f(v[1]):>14s}")
    print("\nSame seed for both policies: any difference is caused by the path-selection policy alone.")
    if a.no_plot:
        return
    if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
    col = {"static": "#eb6834", "dps": "#2a78d6"}
    for tr in ("static", "dps"):
        ts = res[tr][1]
        d = ts[(ts.sec >= cfg.warmup_s) & (ts.sec < cfg.total_s)]
        a1.plot(d.sec - cfg.warmup_s, d.rt_p95_ms, color=col[tr], label=f"{'Static' if tr == 'static' else 'Dynamic'} path selection")
        a2.plot(d.sec - cfg.warmup_s, 100 * d.branches_on_B_frac, color=col[tr])
    if a.condition != "steady":
        for ax in (a1, a2):
            ax.axvspan(cfg.fault_at_s, cfg.fault_at_s + cfg.fault_duration_s, color="#c3c2b7", alpha=0.3)
    a1.set_yscale("log"); a1.set_ylabel("p95 response time per second (ms)"); a1.legend(frameon=False)
    a2.set_ylabel("Branches on Path B (%)"); a2.set_xlabel("Time since start of measurement (s)")
    fig.suptitle(f"Demo: {a.condition}, {a.load} tps per branch (Python model-based simulation)", x=0.01, ha="left")
    fig.tight_layout()
    out = os.path.join(HERE, "outputs", f"demo_{a.condition}_{a.load}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"Chart saved to {out}")
    if matplotlib.get_backend().lower() != "agg":
        plt.show()


if __name__ == "__main__":
    main()
