"""
figures.py - all result graphs, generated only from the CSV outputs.
Every figure carries the label "Python model-based simulation".
"""
import glob, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"static": "#eb6834", "dps": "#2a78d6"}
NAME = {"static": "Static Path Selection", "dps": "Dynamic Path Selection"}
INK, INK2, GRID_C, AX = "#0b0b0b", "#52514e", "#e4e3dd", "#b5b4ad"
TAG = "Python model-based simulation results (not real-world measurements)"
CONDS = ["steady", "brownout", "blackout"]
CTITLE = {"steady": "Steady state", "brownout": "Brownout on Path A (P1)", "blackout": "Blackout on Path A (P2)"}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
                     "axes.edgecolor": AX, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID_C, linewidth=0.8)
    ax.set_axisbelow(True)


def finish(fig, path, title):
    fig.suptitle(title, x=0.01, ha="left", fontsize=11.5, color=INK, y=0.995)
    fig.text(0.01, 0.005, TAG, fontsize=7.5, color=INK2, ha="left", va="bottom")
    top = 0.96
    ax = getattr(fig, "_legend_ax", None)
    if ax is not None:          # one legend row under the title, clear of the data
        h, l = ax.get_legend_handles_labels()
        fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.01, 0.945), ncol=len(l), frameon=False, fontsize=8.5)
        top = 0.89
    fig.tight_layout(rect=(0, 0.03, 1, top))
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def legend(ax, loc="upper left"):
    ax.figure._legend_ax = ax


def by_load(runs, cond, metric, ax, ylabel, logy=False):
    loads = sorted(runs.load_tps.unique())
    x = np.arange(len(loads))
    # Lines share the same x so identical results overlap exactly (static drawn wider
    # underneath); individual runs are shown as dots, nudged sideways for visibility.
    for j, tr in enumerate(("static", "dps")):
        g = runs[(runs.condition == cond) & (runs.treatment == tr)]
        means = [g[g.load_tps == L][metric].mean() for L in loads]
        off = (j - 0.5) * 0.16
        for i, L in enumerate(loads):
            v = g[g.load_tps == L][metric].dropna().values
            ax.scatter(np.full(len(v), x[i] + off), v, s=12, color=COL[tr], alpha=0.45, linewidth=0)
        if tr == "static":
            ax.plot(x, means, color=COL[tr], linewidth=3.4, marker="o", markersize=7, label=NAME[tr], zorder=3)
        else:
            ax.plot(x, means, color=COL[tr], linewidth=1.6, marker="s", markersize=4.5, label=NAME[tr], zorder=4)
    ax.set_xticks(x); ax.set_xticklabels([f"{L}" for L in loads])
    ax.set_xlabel("Offered load per branch (tps)")
    ax.set_ylabel(ylabel)
    if logy:
        ax.set_yscale("log")
    style(ax)


def fig_rt(runs, out, metric, fname, label):
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6), sharey=True)
    for ax, c in zip(axs, CONDS):
        by_load(runs, c, metric, ax, label if c == "steady" else "")
        ax.set_title(CTITLE[c], loc="left", color=INK)
    legend(axs[0])
    axs[0].set_ylim(bottom=0)
    return finish(fig, os.path.join(out, fname), f"{label} by load and network condition (dots = individual runs, line = mean)")


def fig_availability(runs, out):
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    specs = [("fault_txn_availability_pct", "Transaction availability (%)"),
             ("fault_service_availability_pct", "End-to-end service availability (%)"),
             ("fault_sla_compliant_time_pct", "SLA-compliant service time (%)")]
    for ax, (m, lab) in zip(axs, specs):
        x = np.arange(2)
        for j, tr in enumerate(("static", "dps")):
            vals = [runs[(runs.condition == c) & (runs.treatment == tr)][m].mean() for c in ("brownout", "blackout")]
            b = ax.bar(x + (j - 0.5) * 0.36, vals, 0.34, color=COL[tr], label=NAME[tr])
            for xi, v in zip(x + (j - 0.5) * 0.36, vals):
                ax.text(xi, v + 1, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5, color=INK)
        ax.set_xticks(x); ax.set_xticklabels(["Brownout", "Blackout"])
        ax.set_ylim(0, 112); ax.set_title(lab, loc="left", color=INK)
        style(ax)
    legend(axs[0], "lower left")
    return finish(fig, os.path.join(out, "fig03_availability_fault_window.png"),
                  "Three availability measures during the 120 s fault window (mean of runs)")


def fig_unavailability(runs, out):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4))
    loads = sorted(runs.load_tps.unique())
    for ax, (m, lab, scale) in zip(axs, [
            ("fault_service_availability_pct", "Seconds without a usable path per branch\n(blackout, 120 s fault)", 120),
            ("fault_sla_compliant_time_pct", "Seconds on a path outside the SLA per branch\n(brownout, 120 s fault)", 120)]):
        cond = "blackout" if "service" in m else "brownout"
        x = np.arange(len(loads))
        for j, tr in enumerate(("static", "dps")):
            g = runs[(runs.condition == cond) & (runs.treatment == tr)]
            vals = [(100 - g[g.load_tps == L][m].mean()) / 100 * scale for L in loads]
            ax.bar(x + (j - 0.5) * 0.36, vals, 0.34, color=COL[tr], label=NAME[tr])
            for xi, v in zip(x + (j - 0.5) * 0.36, vals):
                ax.text(xi, v, f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, color=INK)
        ax.set_xticks(x); ax.set_xticklabels(loads); ax.set_xlabel("Offered load per branch (tps)")
        ax.set_ylabel(lab); style(ax)
    legend(axs[0], "upper right")
    return finish(fig, os.path.join(out, "fig04_unavailable_time.png"),
                  "Service time lost or degraded during the fault, by load")


def fig_loss(runs, out):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4))
    for ax, c in zip(axs, ("brownout", "blackout")):
        by_load(runs, c, "fault_msg_loss_pct", ax, "Message loss in fault window (%)")
        ax.set_title(CTITLE[c], loc="left", color=INK); ax.set_ylim(bottom=0)
    legend(axs[0], "center right")
    return finish(fig, os.path.join(out, "fig05_packet_loss.png"),
                  "Message (packet) loss experienced by transactions during the fault")


def fig_throughput(runs, data_dir, out):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4), gridspec_kw=dict(width_ratios=[1, 1.4]))
    by_load(runs, "blackout", "fault_throughput_tps", axs[0], "Successful tps in fault window (3 branches)")
    axs[0].set_title("Fault-window throughput, blackout (by send time)", loc="left", color=INK)
    axs[0].set_ylim(bottom=0)
    ax = axs[1]
    for tr in ("static", "dps"):
        f = glob.glob(os.path.join(data_dir, f"transactions_{'SPS' if tr == 'static' else 'DPS'}_L300_blackout_r4.csv.gz"))
        if not f:
            continue
        d = pd.read_csv(f[0])
        ok = d[d.success]
        done = ok.send_time_s + ok.response_time_ms / 1000
        sec = np.floor(done - 60).astype(int)
        c = sec.value_counts().sort_index()
        c = c[(c.index >= 170) & (c.index <= 200)]
        ax.plot(c.index, c.values, color=COL[tr], linewidth=1.8, label=NAME[tr], drawstyle="steps-post")
    ax.axvline(180, color=INK2, linewidth=0.8, linestyle="--")
    ax.text(180.2, ax.get_ylim()[1] * 0.98, "fault onset", fontsize=7.5, color=INK2, va="top")
    ax.set_xlabel("Time since start of measurement (s)"); ax.set_ylabel("Responses completed per second")
    ax.set_title("Completed responses per second around the blackout (L300, r4)", loc="left", color=INK)
    style(ax); legend(ax, "lower right")
    return finish(fig, os.path.join(out, "fig06_throughput.png"), "Transaction throughput")


def fig_failover(runs, out):
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4))
    for ax, (m, lab) in zip(axs, [("failover_time_s_median", "Failover time (s)"),
                                   ("failback_time_s_median", "Fail-back time after fault removal (s)")]):
        x = np.arange(2)
        for j, tr in enumerate(("static", "dps")):
            for i, c in enumerate(("brownout", "blackout")):
                v = runs[(runs.condition == c) & (runs.treatment == tr)][m].dropna().values
                xs = np.full(len(v), i + (j - 0.5) * 0.3) + np.random.default_rng(3).uniform(-0.05, 0.05, len(v))
                ax.scatter(xs, v, s=22, color=COL[tr], alpha=0.75, linewidth=0, label=NAME[tr] if i == 0 else None)
                if len(v):
                    ax.hlines(np.median(v), i + (j - 0.5) * 0.3 - 0.1, i + (j - 0.5) * 0.3 + 0.1, color=INK, linewidth=1.5)
                else:
                    ax.text(i + (j - 0.5) * 0.3, ax.get_ylim()[1] * 0.08 + 0.3, "static never\nswitches", ha="center",
                            fontsize=7.5, color=COL[tr])
        ax.set_xticks(x); ax.set_xticklabels(["Brownout", "Blackout"]); ax.set_ylabel(lab)
        ax.set_xlim(-0.6, 1.6)
        ax.set_ylim(bottom=0); style(ax)
    legend(axs[0], "upper left")
    return finish(fig, os.path.join(out, "fig07_failover.png"),
                  "Failover and fail-back times per run (black bar = median)")


def fig_timeseries(data_dir, out, cond, rep, fname):
    ts = pd.read_csv(os.path.join(data_dir, "timeseries_per_second.csv.gz"))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10.5, 5), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
    for tr in ("static", "dps"):
        rid = f"{'SPS' if tr == 'static' else 'DPS'}_L300_{cond}_r{rep}"
        d = ts[(ts.run_id == rid) & (ts.sec >= 60) & (ts.sec < 480)].copy()
        d["t"] = d.sec - 60
        a1.plot(d.t, d.rt_p95_ms, color=COL[tr], linewidth=1.4, label=f"{NAME[tr]} ({rid})")
        a2.plot(d.t, 100 * d.branches_on_B_frac, color=COL[tr], linewidth=1.6)
    for ax in (a1, a2):
        ax.axvspan(180, 300, color="#c3c2b7", alpha=0.25, linewidth=0); style(ax)
    a1.set_yscale("log"); a1.set_ylabel("p95 response time\nper second (ms, log)")
    a2.set_ylabel("Branches on\nPath B (%)"); a2.set_ylim(-5, 105)
    a2.set_xlabel("Time since start of measurement (s); shaded = fault 180-300 s")
    legend(a1)
    return finish(fig, os.path.join(out, fname), f"Representative {cond} run, 300 tps per branch")


def fig_monitor(data_dir, out, cfg_sla=(60, 10, 1)):
    f = os.path.join(data_dir, "dps_monitor_branch1_DPS_L300_brownout_r1.csv")
    if not os.path.exists(f):
        return None
    m = pd.read_csv(f)
    m = m[(m.t >= 230) & (m.t <= 390)]
    m["ts"] = m.t - 60
    fig, axs = plt.subplots(4, 1, figsize=(10.5, 6.4), sharex=True)
    specs = [("lat_A", "Latency (ms)", cfg_sla[0]), ("jit_A", "Jitter (ms)", cfg_sla[1]), ("loss_A", "Loss (%)", cfg_sla[2])]
    for ax, (c, lab, th) in zip(axs, specs):
        ax.plot(m.ts, m[c].replace(np.inf, np.nan), color="#2a78d6", linewidth=1.4, label="Path A, DPS monitor")
        ax.plot(m.ts, m[c.replace("_A", "_B")].replace(np.inf, np.nan), color="#1baf7a", linewidth=1.2, label="Path B, DPS monitor")
        ax.axhline(th, color="#e34948", linewidth=1, linestyle="--")
        ax.text(m.ts.max(), th, f" SLA {th:g}", color="#e34948", fontsize=7.5, va="center")
        ax.set_ylabel(lab); style(ax)
    axs[0].legend(frameon=False, fontsize=8, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    axs[3].step(m.ts, m.selected.map({1: 1, 2: 2, 0: 0}), where="post", color=INK, linewidth=1.4)
    axs[3].set_yticks([1, 2]); axs[3].set_yticklabels(["Path A", "Path B"]); axs[3].set_ylim(0.5, 2.5)
    axs[3].set_ylabel("Selected"); style(axs[3])
    for ax in axs:
        ax.axvspan(180, 300, color="#c3c2b7", alpha=0.25, linewidth=0)
    axs[3].set_xlabel("Time since start of measurement (s); shaded = brownout")
    return finish(fig, os.path.join(out, "fig10_dps_monitor_brownout.png"),
                  "How dynamic path selection decides: monitored SLA metrics, branch 1, run DPS_L300_brownout_r1")


def fig_switching(runs, out):
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=True)
    for ax, c in zip(axs, CONDS):
        by_load(runs, c, "switches_per_branch_hour", ax, "Path switches per branch-hour" if c == "steady" else "")
        ax.set_title(CTITLE[c], loc="left", color=INK); ax.set_ylim(bottom=0)
    legend(axs[0])
    return finish(fig, os.path.join(out, "fig11_switching_frequency.png"),
                  "Path-switching frequency (note: flapping of dynamic selection at 450 tps)")


def fig_components(runs, out):
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    labels, net, proc, retx = [], [], [], []
    for c in CONDS:
        for tr in ("static", "dps"):
            g = runs[(runs.condition == c) & (runs.treatment == tr)]
            labels.append(f"{c}\n{'Static' if tr == 'static' else 'Dynamic'}")
            net.append(g.net_rtt_mean_ms.mean()); proc.append(g.proc_mean_ms.mean()); retx.append(g.retx_wait_mean_ms.mean())
    x = np.arange(len(labels))
    ax.bar(x, net, 0.6, color="#2a78d6", label="Network delay (request + response)")
    ax.bar(x, proc, 0.6, bottom=net, color="#1baf7a", label="HQ application processing")
    ax.bar(x, retx, 0.6, bottom=np.array(net) + np.array(proc), color="#eda100", label="Retransmission wait")
    for xi, tot in zip(x, np.array(net) + np.array(proc) + np.array(retx)):
        ax.text(xi, tot + 0.5, f"{tot:.1f}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylabel("Mean response time (ms)")
    style(ax); legend(ax)
    return finish(fig, os.path.join(out, "fig12_rt_components.png"),
                  "Mean response time split into network delay, processing and retransmission wait (whole window)")


def fig_sensitivity(sens, out):
    if sens is None or not len(sens):
        return None
    d = sens[(sens.condition == "blackout") & (sens.load_tps == 300)]
    order = ["S0_baseline", "S1_static_no_backup", "S2_static_slow_detection", "S3_policy_delay_1s", "S4_timeout_2s"]
    lab = {"S0_baseline": "Baseline", "S1_static_no_backup": "Static: no backup",
           "S2_static_slow_detection": "Static: 15 s detection", "S3_policy_delay_1s": "+1 s policy delay",
           "S4_timeout_2s": "2 s timeout"}
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.6))
    for ax, (m, yl) in zip(axs, [("fault_txn_availability_pct", "Transaction availability, fault window (%)"),
                                  ("fault_service_availability_pct", "Service availability, fault window (%)")]):
        x = np.arange(len(order))
        for j, tr in enumerate(("static", "dps")):
            vals = [d[(d.scenario == s) & (d.treatment == tr)][m].mean() for s in order]
            ax.bar(x + (j - 0.5) * 0.36, vals, 0.34, color=COL[tr], label=NAME[tr])
            for xi, v in zip(x + (j - 0.5) * 0.36, vals):
                if not np.isnan(v):
                    ax.text(xi, v + 1, f"{v:.1f}", ha="center", fontsize=7, color=INK)
        ax.set_xticks(x); ax.set_xticklabels([lab[s] for s in order], rotation=15, fontsize=8)
        ax.set_ylim(0, 112); ax.set_ylabel(yl); style(ax)
    legend(axs[0], "lower left")
    return finish(fig, os.path.join(out, "fig13_sensitivity_blackout.png"),
                  "Sensitivity analysis, blackout at 300 tps (5 runs per bar; missing bar = scenario not applicable)")


def make_all(out_dir, runs, sens=None):
    fdir = os.path.join(out_dir, "figures"); os.makedirs(fdir, exist_ok=True)
    data = os.path.join(out_dir, "data")
    figs = {}
    figs["rt_p95"] = fig_rt(runs, fdir, "rt_p95_ms", "fig01_response_time_p95.png", "95th percentile response time (ms)")
    figs["rt_p99"] = fig_rt(runs, fdir, "rt_p99_ms", "fig02_response_time_p99.png", "99th percentile response time (ms)")
    figs["availability"] = fig_availability(runs, fdir)
    figs["unavailable"] = fig_unavailability(runs, fdir)
    figs["loss"] = fig_loss(runs, fdir)
    figs["throughput"] = fig_throughput(runs, data, fdir)
    figs["failover"] = fig_failover(runs, fdir)
    figs["ts_brownout"] = fig_timeseries(data, fdir, "brownout", 1, "fig08_timeseries_brownout.png")
    figs["ts_blackout"] = fig_timeseries(data, fdir, "blackout", 4, "fig09_timeseries_blackout.png")
    figs["monitor"] = fig_monitor(data, fdir)
    figs["switching"] = fig_switching(runs, fdir)
    figs["components"] = fig_components(runs, fdir)
    figs["sensitivity"] = fig_sensitivity(sens, fdir)
    print(f"Figures written to {fdir}")
    return {k: v for k, v in figs.items() if v}
