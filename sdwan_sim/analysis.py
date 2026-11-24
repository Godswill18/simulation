"""
analysis.py - aggregation, comparison tables and statistical tests.

Unit of analysis: the run (80 runs). Transactions inside a run share one
network state, so they are reduced to run-level metrics first.

Pairing: static and dynamic runs of the same cell (load, condition,
repetition) use the same random numbers, so the comparison is PAIRED.
Test: Wilcoxon signed-rank, two-sided, alpha = 0.05, on the paired
differences d = static - dynamic. Effect size: matched-pairs rank-biserial
correlation r_rb (positive = static larger). Assumption check: the Wilcoxon
test assumes the differences are symmetric about their median; the
assumption-free sign test is reported alongside. Holm correction is applied
within each hypothesis family. If every paired difference is exactly zero
the outcomes are identical and no test is run.

Confirmatory pooling follows Chapter 3: runs are pooled across the four loads
within each condition (steady 20 pairs, brownout 12 pairs, blackout 8 pairs).
Per-load comparisons are descriptive (5, 3 and 2 pairs are too few for tests).
"""
import json, math, os
import numpy as np
import pandas as pd
from scipy import stats

LABEL = "Python model-based simulation results (not real-world measurements)"
T = {"static": "Static", "dps": "Dynamic"}

METRIC_NAMES = {
    "rt_mean_ms": "Mean response time (ms)", "rt_median_ms": "Median response time (ms)",
    "rt_p95_ms": "95th percentile response time (ms)", "rt_p99_ms": "99th percentile response time (ms)",
    "rt_p95_incl_failures_ms": "p95 response time, failures counted as 10 s (ms)",
    "txn_availability_pct": "Transaction availability (%)",
    "service_availability_pct": "End-to-end service availability (%)",
    "sla_compliant_time_pct": "SLA-compliant service time (%)",
    "throughput_tps": "Throughput (successful tps, 3 branches)",
    "net_rtt_mean_ms": "Network latency, mean RTT (ms)", "jitter_ms": "Jitter (ms)",
    "msg_loss_pct": "Message loss (%)", "failover_time_s_median": "Failover time (s)",
    "failback_time_s_median": "Fail-back time (s)", "recovery_time_s_median": "Recovery time (s)",
    "max_outage_s_median": "Longest gap between successful responses (s)",
    "path_switches": "Path switches per run", "switches_per_branch_hour": "Path switches per branch-hour",
    "proc_mean_ms": "Application processing, mean (ms)", "retx_wait_mean_ms": "Retransmission wait, mean (ms)",
    "share_via_path_B_pct": "Transactions carried on Path B (%)", "failed": "Failed transactions",
}


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x:,.{nd}f}"


def fp(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def paired_test(df, metric, condition):
    d = df[df.condition == condition]
    piv = d.pivot_table(index="cell_id", columns="treatment", values=metric, aggfunc="first").dropna()
    out = {"metric": metric, "metric_name": METRIC_NAMES.get(metric, metric), "condition": condition,
           "n_pairs": len(piv)}
    if len(piv) == 0 or "static" not in piv or "dps" not in piv:
        out.update(note="not testable (metric undefined for one policy)", p=np.nan)
        return out
    x, y = piv["static"].values, piv["dps"].values
    diff = x - y
    nz = diff[diff != 0]
    out.update(mean_static=float(x.mean()), mean_dps=float(y.mean()), median_static=float(np.median(x)),
               median_dps=float(np.median(y)), median_diff=float(np.median(diff)),
               n_nonzero=int(nz.size), n_static_higher=int((diff > 0).sum()), n_dps_higher=int((diff < 0).sum()))
    if nz.size == 0:
        out.update(note="identical in every pair (no test)", p=np.nan, W=np.nan, r_rb=0.0, sign_p=np.nan)
        return out
    ranks = stats.rankdata(np.abs(nz))
    wp, wm = ranks[nz > 0].sum(), ranks[nz < 0].sum()
    out["r_rb"] = float((wp - wm) / (wp + wm))
    res = stats.wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
    out["W"], out["p"] = float(res.statistic), float(res.pvalue)
    out["sign_p"] = float(stats.binomtest(int((nz > 0).sum()), nz.size, 0.5).pvalue)
    out["diff_skew"] = float(stats.skew(nz)) if nz.size > 2 else np.nan
    out["note"] = ""
    return out


def holm(ps):
    idx = [i for i, p in enumerate(ps) if not (p is None or math.isnan(p))]
    adj = [np.nan] * len(ps)
    running = 0.0
    for rank, i in enumerate(sorted(idx, key=lambda i: ps[i])):
        running = max(running, min(1.0, (len(idx) - rank) * ps[i]))
        adj[i] = running
    return adj


def describe(runs, metrics, by):
    rows = []
    for keys, g in runs.groupby(by):
        r = dict(zip(by, keys if isinstance(keys, tuple) else (keys,)))
        r["n_runs"] = len(g)
        for m in metrics:
            v = g[m].dropna()
            r[f"{m}_mean"] = v.mean() if len(v) else np.nan
            r[f"{m}_sd"] = v.std(ddof=1) if len(v) > 1 else np.nan
            r[f"{m}_min"] = v.min() if len(v) else np.nan
            r[f"{m}_max"] = v.max() if len(v) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def run_all(out_dir, runs, sens=None):
    tdir = os.path.join(out_dir, "tables"); os.makedirs(tdir, exist_ok=True)
    tables = {}
    conds = ["steady", "brownout", "blackout"]
    order = {"steady": 0, "brownout": 1, "blackout": 2}

    # 1 design
    des = runs.groupby(["treatment", "load_tps", "condition_group", "condition"]).size().reset_index(name="runs")
    tables["design"] = des

    # 2 aggregated (treatment x load x condition)
    key = ["rt_mean_ms", "rt_median_ms", "rt_p95_ms", "rt_p99_ms", "txn_availability_pct",
           "service_availability_pct", "sla_compliant_time_pct", "throughput_tps", "net_rtt_mean_ms",
           "jitter_ms", "msg_loss_pct", "path_switches", "share_via_path_B_pct", "failed"]
    agg = describe(runs, key, ["condition", "load_tps", "treatment"])
    agg["_o"] = agg.condition.map(order); agg = agg.sort_values(["_o", "load_tps", "treatment"]).drop(columns="_o")
    tables["aggregated_by_load"] = agg

    # 3 response time table by load (means across reps)
    rows = []
    for c in conds:
        for L in sorted(runs.load_tps.unique()):
            r = {"Condition": c, "Load (tps)": L}
            for tr in ("static", "dps"):
                g = runs[(runs.condition == c) & (runs.load_tps == L) & (runs.treatment == tr)]
                r[f"{T[tr]} mean"] = fmt(g.rt_mean_ms.mean())
                r[f"{T[tr]} p95"] = fmt(g.rt_p95_ms.mean())
                r[f"{T[tr]} p99"] = fmt(g.rt_p99_ms.mean())
            rows.append(r)
    tables["response_time_by_load"] = pd.DataFrame(rows)

    # 4 availability (full window and fault window)
    rows = []
    for c in conds:
        for tr in ("static", "dps"):
            g = runs[(runs.condition == c) & (runs.treatment == tr)]
            rows.append({"Condition": c, "Policy": T[tr], "Runs": len(g),
                         "WAN link avail. Path A (%)": fmt(g.link_availability_A_pct.mean(), 3),
                         "Service avail. (%)": fmt(g.service_availability_pct.mean(), 3),
                         "SLA-compliant time (%)": fmt(g.sla_compliant_time_pct.mean(), 3),
                         "Transaction avail. (%)": fmt(g.txn_availability_pct.mean(), 4),
                         "Fault-window service avail. (%)": fmt(g.get("fault_service_availability_pct", pd.Series(dtype=float)).mean(), 3),
                         "Fault-window SLA-compliant (%)": fmt(g.get("fault_sla_compliant_time_pct", pd.Series(dtype=float)).mean(), 3),
                         "Fault-window txn avail. (%)": fmt(g.get("fault_txn_availability_pct", pd.Series(dtype=float)).mean(), 4),
                         "Failed txns (mean/run)": fmt(g.failed.mean(), 1)})
    tables["availability"] = pd.DataFrame(rows)

    # 5 failover performance
    rows = []
    for c in ("brownout", "blackout"):
        for L in sorted(runs.load_tps.unique()):
            for tr in ("static", "dps"):
                g = runs[(runs.condition == c) & (runs.load_tps == L) & (runs.treatment == tr)]
                rows.append({"Condition": c, "Load (tps)": L, "Policy": T[tr],
                             "Failover time (s)": fmt(g.failover_time_s_median.mean()),
                             "Branches on B at onset": fmt(g.branches_on_B_at_fault_onset.mean(), 1),
                             "Recovery time (s)": fmt(g.recovery_time_s_median.mean()),
                             "Fail-back time (s)": fmt(g.failback_time_s_median.mean()),
                             "Longest outage (s)": fmt(g.max_outage_s_median.mean()),
                             "Fault-window p95 RT (ms)": fmt(g.fault_rt_p95_ms.mean()),
                             "Fault-window on Path B (%)": fmt(g.fault_share_via_path_B_pct.mean(), 1)})
    tables["failover"] = pd.DataFrame(rows)

    # 6 network metrics
    rows = []
    for c in conds:
        pre = "" if c == "steady" else "fault_"
        for tr in ("static", "dps"):
            g = runs[(runs.condition == c) & (runs.treatment == tr)]
            rows.append({"Condition": c, "Window": "measurement" if c == "steady" else "fault", "Policy": T[tr],
                         "Latency, mean RTT (ms)": fmt(g[f"{pre}net_rtt_mean_ms"].mean()),
                         "Jitter (ms)": fmt(g[f"{pre}jitter_ms"].mean()),
                         "Message loss (%)": fmt(g[f"{pre}msg_loss_pct"].mean(), 3),
                         "Throughput (tps)": fmt(g[f"{pre}throughput_tps"].mean(), 1),
                         "Retransmitted txns (%)": fmt(g[f"{pre}retransmitted_share_pct"].mean(), 3),
                         "Path switches / branch-hour": fmt(g.switches_per_branch_hour.mean(), 1)})
    tables["network"] = pd.DataFrame(rows)

    # 7 response-time components
    rows = []
    for c in conds:
        for tr in ("static", "dps"):
            g = runs[(runs.condition == c) & (runs.treatment == tr)]
            rows.append({"Condition": c, "Policy": T[tr], "Mean RT (ms)": fmt(g.rt_mean_ms.mean()),
                         "Network delay (ms)": fmt(g.net_rtt_mean_ms.mean()),
                         "Application processing (ms)": fmt(g.proc_mean_ms.mean()),
                         "Retransmission wait (ms)": fmt(g.retx_wait_mean_ms.mean(), 3)})
    tables["rt_components"] = pd.DataFrame(rows)

    # 8 statistics
    conf_spec = [("H01", "rt_p95_ms", c) for c in conds] + \
                [("H02", m, c) for c in ("brownout", "blackout")
                 for m in ("fault_txn_availability_pct", "fault_service_availability_pct", "fault_sla_compliant_time_pct")]
    conf = []
    for h, m, c in conf_spec:
        r = paired_test(runs, m, c); r["hypothesis"] = h; conf.append(r)
    for r, p in zip(conf, holm([r["p"] for r in conf])):
        r["p_holm"] = p
    h3_spec = []
    for c in conds:
        pre = "" if c == "steady" else "fault_"
        for m in ("net_rtt_mean_ms", "jitter_ms", "msg_loss_pct", "throughput_tps"):
            h3_spec.append((f"{pre}{m}", c))
    h3_spec.append(("failover_time_s_median", "blackout"))
    h3 = []
    for m, c in h3_spec:
        r = paired_test(runs, m, c); r["hypothesis"] = "H03"; h3.append(r)
    for r, p in zip(h3, holm([r["p"] for r in h3])):
        r["p_holm"] = p
    for r in conf + h3:
        r["metric_name"] = METRIC_NAMES.get(r["metric"].replace("fault_", ""), r["metric"]) + \
            (" [fault window]" if r["metric"].startswith("fault_") else "")
    stats_df = pd.DataFrame(conf + h3)
    tables["statistical_tests"] = stats_df

    def disp(rows):
        return pd.DataFrame([{
            "Hypothesis": r["hypothesis"], "Metric": r["metric_name"], "Condition": r["condition"],
            "Pairs": r["n_pairs"], "Mean static": fmt(r.get("mean_static")), "Mean dynamic": fmt(r.get("mean_dps")),
            "Median diff (S-D)": fmt(r.get("median_diff"), 3), "Wilcoxon p (Holm)": fp(r.get("p_holm")),
            "Sign-test p": fp(r.get("sign_p")), "r_rb": fmt(r.get("r_rb")), "Note": r.get("note", "")} for r in rows])
    tables["tests_confirmatory"] = disp(conf)
    tables["tests_H03"] = disp(h3)

    # decisions
    want = {"rt_p95_ms": "lower", "fault_txn_availability_pct": "higher",
            "fault_service_availability_pct": "higher", "fault_sla_compliant_time_pct": "higher"}
    dec = []
    for r in conf:
        if r.get("note", "").startswith("identical"):
            d = "Fail to reject (identical outcomes)"
        elif math.isnan(r.get("p_holm", np.nan)):
            d = "Not testable"
        else:
            good = r["median_diff"] > 0 if want[r["metric"]] == "lower" else r["median_diff"] < 0
            d = "Reject" if (r["p_holm"] < 0.05 and good) else "Fail to reject"
        dec.append({"Hypothesis": r["hypothesis"], "Metric": r["metric_name"], "Condition": r["condition"],
                    "Holm p": fp(r.get("p_holm")), "Decision": d})
    sig3 = [r for r in h3 if not math.isnan(r.get("p_holm", np.nan)) and r["p_holm"] < 0.05]
    dec.append({"Hypothesis": "H03", "Metric": "Latency, jitter, loss, throughput (3 conditions), failover time (blackout)",
                "Condition": "all", "Holm p": fp(min([r["p_holm"] for r in sig3], default=np.nan)),
                "Decision": ("Reject" if sig3 else "Fail to reject") +
                f" ({len(sig3)} of {len(h3)} metrics differ significantly)"})
    tables["hypothesis_decisions"] = pd.DataFrame(dec)

    # 9 sensitivity
    if sens is not None and len(sens):
        base = sens[sens.scenario == "S0_baseline"]
        rows = []
        for (sc, tr, c, L), g in sens.groupby(["scenario", "treatment", "condition", "load_tps"]):
            b = base[(base.treatment == tr) & (base.condition == c) & (base.load_tps == L)]
            def m(df, col):
                return df[col].mean() if col in df and len(df) else np.nan
            rows.append({"Scenario": sc, "Description": g.scenario_description.iloc[0], "Policy": T[tr],
                         "Condition": c, "Load": L, "Runs": len(g),
                         "Fault txn avail. (%)": fmt(m(g, "fault_txn_availability_pct"), 3),
                         "Baseline": fmt(m(b, "fault_txn_availability_pct"), 3),
                         "Fault svc avail. (%)": fmt(m(g, "fault_service_availability_pct"), 2),
                         "p95 RT (ms)": fmt(m(g, "rt_p95_ms")), "Baseline p95": fmt(m(b, "rt_p95_ms")),
                         "p99 RT (ms)": fmt(m(g, "rt_p99_ms")),
                         "Failover (s)": fmt(m(g, "failover_time_s_median")),
                         "Switches/run": fmt(m(g, "path_switches"), 0)})
        st = pd.DataFrame(rows)
        st = st[st.Scenario != "S0_baseline"]
        tables["sensitivity"] = st
        tables["sensitivity_baseline"] = pd.DataFrame([r for r in rows if r["Scenario"] == "S0_baseline"])

    # write
    for k, v in tables.items():
        v.to_csv(os.path.join(tdir, f"{k}.csv"), index=False)
    with open(os.path.join(tdir, "all_tables.md"), "w") as f:
        f.write(f"# {LABEL}\n\n")
        for k in ("design", "response_time_by_load", "rt_components", "availability", "failover", "network",
                  "tests_confirmatory", "tests_H03", "hypothesis_decisions", "sensitivity"):
            if k in tables:
                f.write(f"## {k}\n\n{md(tables[k])}\n\n")
    try:
        with pd.ExcelWriter(os.path.join(out_dir, "results_workbook.xlsx")) as xw:
            pd.DataFrame({"Note": [LABEL, "Each row of run_level_results is one simulation run.",
                                   "Seeds and parameters: parameters.json"]}).to_excel(xw, "README", index=False)
            runs.to_excel(xw, "run_level_results", index=False)
            for k, v in tables.items():
                v.to_excel(xw, k[:31], index=False)
    except Exception as e:
        print("Excel workbook skipped:", e)
    print(f"Tables written to {tdir}")
    return tables
