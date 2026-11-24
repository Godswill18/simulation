"""
run.py - one simulation run (one treatment x load x condition x repetition)
and the reduction of its transactions to run-level metrics.

AVAILABILITY - three different measures, never used interchangeably:

  1. WAN link availability (per path, ground truth of the model)
        A_link(p) = time path p can deliver traffic / measurement time x 100
     A path is "up" unless it is in blackout (loss = 100 %). A brownout path is up.

  2. End-to-end service availability (time based, per branch)
        A_svc = time the branch's selected path is up / measurement time x 100
     i.e. the share of time during which a transaction sent by the branch
     could reach the HQ core banking service at all.

  3. Transaction availability (successful banking transactions)  - PRIMARY
        A_txn = successful transactions / transactions attempted x 100
     A transaction is successful if its response arrives within 10 s of the
     first send. This is the formula of Section 1.5.

  Supplementary: SLA-compliant service time
        A_sla = time the selected path meets the SLA thresholds / measurement time x 100
     (shows "available but degraded" periods that A_svc counts as available).

All measures use the measurement window [60 s, 480 s) by transaction send time
(or grid time); the fault-window versions use [240 s, 360 s).
"""
import time
import numpy as np
import pandas as pd
from .network import Conditions
from .monitor import run_dps, run_static, GRID
from .transactions import simulate_branch

COND_CODE = {"steady": 0, "brownout": 1, "blackout": 2}
TREAT_LABEL = {"static": "Static Path Selection", "dps": "Dynamic Path Selection"}


def run_id(treatment, load, condition, rep):
    return f"{'SPS' if treatment == 'static' else 'DPS'}_L{load:03d}_{condition}_r{rep}"


def cell_id(load, condition, rep):
    return f"L{load:03d}_{condition}_r{rep}"


def _q(x, p):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return float(np.percentile(x, p)) if x.size else np.nan


def _mean(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return float(x.mean()) if x.size else np.nan


def simulate_run(cfg, treatment, load, condition, rep, keep_detail=False):
    t_wall = time.time()
    cond = Conditions(cfg, condition)
    base_seed = [cfg.master_seed, int(load), COND_CODE[condition], int(rep)]
    branches, monitors = [], []
    for b in range(1, cfg.n_branches + 1):
        mon_rng = np.random.default_rng(base_seed + [b, 50 if treatment == "dps" else 51])
        mon = (run_dps if treatment == "dps" else run_static)(cfg, cond, load, mon_rng, b)
        res = simulate_branch(cfg, cond, mon, load, base_seed + [b])
        res["branch"] = b
        branches.append(res)
        monitors.append(mon)

    ws, we = cfg.warmup_s, cfg.total_s
    fon, foff = cfg.fault_on, cfg.fault_off
    has_fault = condition != "steady"
    s = {"run_id": run_id(treatment, load, condition, rep), "cell_id": cell_id(load, condition, rep),
         "treatment": treatment, "policy": TREAT_LABEL[treatment], "load_tps": load,
         "condition": condition, "rep": rep, "seed": "-".join(map(str, base_seed))}

    def txn_metrics(lo, hi, prefix):
        att = ok = 0
        rts, rts_wt, nets, procs, retx = [], [], [], [], []
        sent = lost = nopath = retx_needed = via_b = 0
        jit_b = []
        for r in branches:
            m = (r["arr"] >= lo) & (r["arr"] < hi)
            succ = r["success"][m]
            att += int(m.sum()); ok += int(succ.sum())
            rt = r["rt"][m]
            rts.append(rt[succ])
            rts_wt.append(np.where(succ, rt, cfg.timeout_s))
            nets.append(r["net"][m][succ]); procs.append(r["proc"][m][succ]); retx.append(r["retx_wait"][m][succ])
            sent += int(r["sent_msgs"][m].sum()); lost += int(r["lost_msgs"][m].sum())
            nopath += int(r["nopath"][m].sum())
            retx_needed += int((r["attempt"][m][succ] > 1).sum())
            via_b += int((r["path"][m][succ] == 2).sum())
            net_sorted = r["net"][m][succ]          # arrivals are already in time order
            if net_sorted.size > 1:
                jit_b.append(np.mean(np.abs(np.diff(net_sorted))))
        rts = np.concatenate(rts) * 1000; rts_wt = np.concatenate(rts_wt) * 1000
        nets = np.concatenate(nets) * 1000
        dur = hi - lo
        return {
            f"{prefix}attempted": att, f"{prefix}successful": ok, f"{prefix}failed": att - ok,
            f"{prefix}txn_availability_pct": 100.0 * ok / att if att else np.nan,
            f"{prefix}rt_mean_ms": _mean(rts), f"{prefix}rt_median_ms": _q(rts, 50),
            f"{prefix}rt_p95_ms": _q(rts, 95), f"{prefix}rt_p99_ms": _q(rts, 99),
            f"{prefix}rt_p95_incl_failures_ms": _q(rts_wt, 95),
            f"{prefix}net_rtt_mean_ms": _mean(nets),
            f"{prefix}proc_mean_ms": _mean(np.concatenate(procs) * 1000),
            f"{prefix}retx_wait_mean_ms": _mean(np.concatenate(retx) * 1000),
            f"{prefix}jitter_ms": _mean(np.array(jit_b) * 1000) if jit_b else np.nan,
            f"{prefix}msg_loss_pct": 100.0 * lost / sent if sent else np.nan,
            f"{prefix}retransmitted_share_pct": 100.0 * retx_needed / ok if ok else np.nan,
            f"{prefix}no_path_attempts": nopath,
            f"{prefix}share_via_path_B_pct": 100.0 * via_b / ok if ok else np.nan,
            f"{prefix}throughput_tps": ok / dur,
        }

    s.update(txn_metrics(ws, we, ""))
    if has_fault:
        s.update(txn_metrics(fon, foff, "fault_"))

    # time-based availability and path behaviour on the 0.2 s grid
    times = monitors[0].times
    gm = (times >= ws) & (times < we)
    gf = (times >= fon) & (times < foff)
    link = {p: cond.link_up(p, times) for p in "AB"}
    sla_t = {p: cond.sla_compliant_truth(p, times) for p in "AB"}
    svc, svc_f, slas, slas_f, switches = [], [], [], [], 0
    fo, fb, rec, outage, on_b_at_fault = [], [], [], [], 0
    for mon, r in zip(monitors, branches):
        sel = mon.sel
        up_sel = np.where(sel == 1, link["A"], np.where(sel == 2, link["B"], False))
        sla_sel = np.where(sel == 1, sla_t["A"], np.where(sel == 2, sla_t["B"], False))
        svc.append(up_sel[gm].mean()); slas.append(sla_sel[gm].mean())
        sw = np.diff(sel[gm].astype(int)) != 0
        switches += int(sw.sum())
        if has_fault:
            svc_f.append(up_sel[gf].mean()); slas_f.append(sla_sel[gf].mean())
            k_on = int(np.searchsorted(times, fon - 1e-9))
            if sel[k_on - 1] == 2:
                # branch was already on Path B when the fault began (e.g. flapping at
                # congested load): no failover to measure for this branch
                on_b_at_fault += 1
                fo.append(np.nan)
            else:
                after = (times >= fon) & (sel == 2)
                fo.append(times[after][0] - fon if after.any() and times[after][0] < foff else np.nan)
            if not np.isnan(fo[-1]):
                back = (times >= foff) & (sel == 1)
                fb.append(times[back][0] - foff if back.any() else np.nan)
            okb = r["success"] & (r["path"] == 2) & (r["done"] >= fon)
            rec.append(r["done"][okb].min() - fon if okb.any() and r["done"][okb].min() < foff else np.nan)
            d = np.sort(r["done"][r["success"]])
            inside = d[(d >= fon) & (d < foff)]
            nxt = d[d >= foff]
            pts = np.concatenate([[fon], inside, [nxt[0] if nxt.size else foff]])
            outage.append(float(np.max(np.diff(pts))))
    s["link_availability_A_pct"] = 100.0 * link["A"][gm].mean()
    s["link_availability_B_pct"] = 100.0 * link["B"][gm].mean()
    s["service_availability_pct"] = 100.0 * float(np.mean(svc))
    s["sla_compliant_time_pct"] = 100.0 * float(np.mean(slas))
    s["path_switches"] = switches
    s["switches_per_branch_hour"] = switches / cfg.n_branches / (cfg.measure_s / 3600.0)
    if has_fault:
        s["fault_link_availability_A_pct"] = 100.0 * link["A"][gf].mean()
        s["fault_service_availability_pct"] = 100.0 * float(np.mean(svc_f))
        s["fault_sla_compliant_time_pct"] = 100.0 * float(np.mean(slas_f))
        fo_ok = [x for x in fo if not np.isnan(x)]
        s["failover_triggered_branches"] = len(fo_ok)
        s["branches_on_B_at_fault_onset"] = on_b_at_fault
        s["failover_time_s_median"] = float(np.median(fo_ok)) if fo_ok else np.nan
        s["failover_time_s_max"] = float(np.max(fo_ok)) if fo_ok else np.nan
        fb_ok = [x for x in fb if not np.isnan(x)]
        s["failback_time_s_median"] = float(np.median(fb_ok)) if fb_ok else np.nan
        rec_ok = [x for x in rec if not np.isnan(x)]
        s["recovery_time_s_median"] = float(np.median(rec_ok)) if rec_ok else np.nan
        s["max_outage_s_median"] = float(np.median(outage))
    s["wall_time_s"] = round(time.time() - t_wall, 2)

    # per-second time series (whole run, all branches pooled)
    sec_rows = []
    allr = pd.concat([pd.DataFrame({"sec": np.floor(r["arr"]).astype(int), "ok": r["success"],
                                    "rt": r["rt"] * 1000, "path": r["path"]}) for r in branches])
    g = allr.groupby("sec")
    ts = pd.DataFrame({"sent": g.size(), "successful": g["ok"].sum()})
    ts["failed"] = ts["sent"] - ts["successful"]
    okr = allr[allr["ok"]]
    go = okr.groupby("sec")
    ts["rt_p95_ms"] = go["rt"].quantile(0.95)
    ts["rt_mean_ms"] = go["rt"].mean()
    ts["share_via_B_pct"] = go["path"].apply(lambda x: 100.0 * (x == 2).mean())
    sel_all = np.vstack([m.sel for m in monitors])
    up_all = np.vstack([np.where(m.sel == 1, link["A"], np.where(m.sel == 2, link["B"], False)) for m in monitors])
    gsec = np.floor(times).astype(int)
    gdf = pd.DataFrame({"sec": gsec, "svc": up_all.mean(0), "onB": (sel_all == 2).mean(0)})
    gdf = gdf[(gdf["sec"] >= 0) & (gdf["sec"] < cfg.total_s)].groupby("sec").mean()
    ts = ts.join(gdf.rename(columns={"svc": "service_available_frac", "onB": "branches_on_B_frac"}), how="outer")
    ts = ts.reset_index().rename(columns={"index": "sec"})
    ts.insert(0, "run_id", s["run_id"])

    events = []
    for m in monitors:
        for e in m.events:
            if 0 <= e["t"] < cfg.total_s:
                events.append(dict(e, run_id=s["run_id"]))

    detail = None
    if keep_detail:
        detail = {
            "transactions": pd.concat([pd.DataFrame({
                "run_id": s["run_id"], "branch": r["branch"], "send_time_s": r["arr"].round(6),
                "success": r["success"], "response_time_ms": (r["rt"] * 1000).round(3),
                "network_delay_ms": (r["net"] * 1000).round(3), "processing_ms": (r["proc"] * 1000).round(3),
                "retransmission_wait_ms": (r["retx_wait"] * 1000).round(3), "attempt": r["attempt"],
                "path": np.array(["none", "A", "B"])[r["path"]], "messages_sent": r["sent_msgs"],
                "messages_lost": r["lost_msgs"]}) for r in branches]),
            "monitor": pd.DataFrame(dict(t=monitors[0].times, selected=monitors[0].sel,
                                         **{k: v for k, v in monitors[0].log.items()})) if monitors[0].log else None,
        }
    return s, ts, events, detail
