"""
transactions.py - banking transaction model (branch -> HQ core banking -> branch).

One transaction = a request message from the branch client to the HQ core
banking service and a response message back (ISO 8583-style 0200/0210 pair).

Response time of a successful transaction:

    RT = R  +  d_up  +  P  +  d_down

  R       retransmission waiting: time from first send to the start of the
          attempt that succeeded (0 if the first attempt succeeded)
  d_up    one-way network delay of the request   (network.py)
  P       HQ application processing time, lognormal (NOT network delay)
  d_down  one-way network delay of the response

Network delay of the transaction = d_up + d_down (reported separately from P).

Loss and retransmission: if the request or the response is lost, the client
transport retransmits after RTO = 0.25 s, doubling each time (0.25, 0.5, 1, 2,
4 s). Attempts start at 0, 0.25, 0.75, 1.75, 3.75 and 7.75 s after the first
send. Every attempt uses the path selected at the moment it is sent (a route
change re-routes the session). A transaction FAILS if no response has arrived
10 s after the first send (no application-level retry).

Queueing: each path has a FIFO queue per direction at the branch access link
(upstream) and at the HQ side (downstream). First attempts get their exact
Lindley waiting time; retransmissions, which are few, see the virtual waiting
time of that queue at their send time.

Common random numbers: arrival times, processing times and every per-attempt
random draw for BOTH paths come from streams seeded only by (load, condition,
repetition, branch), never by the treatment. Static and dynamic runs of the
same cell therefore face identical traffic and identical randomness; only the
path-selection policy differs.
"""
import numpy as np
from .network import lindley_waits, virtual_wait

MAX_ATTEMPTS = 8


def attempt_offsets(cfg):
    offs, t, rto = [0.0], 0.0, cfg.rto_initial_s
    while True:
        t += rto
        rto *= cfg.rto_backoff
        if t >= cfg.timeout_s or len(offs) >= MAX_ATTEMPTS:
            return np.array(offs)
        offs.append(t)


def simulate_branch(cfg, cond, monitor, load_tps, seed_seq):
    """Simulate all transactions of one branch for one run.
    seed_seq: list of ints identifying (cell, branch) - independent of treatment."""
    rng_arr = np.random.default_rng(seed_seq + [1])
    # Poisson arrivals over [0, total)
    n_exp = int(load_tps * cfg.total_s * 1.2 + 50)
    gaps = rng_arr.exponential(1.0 / load_tps, n_exp)
    arr = np.cumsum(gaps)
    while arr[-1] < cfg.total_s:
        arr = np.concatenate([arr, arr[-1] + np.cumsum(rng_arr.exponential(1.0 / load_tps, n_exp // 4))])
    arr = arr[arr < cfg.total_s]
    n = arr.size
    proc = np.exp(np.log(cfg.proc_median_ms / 1000.0) + cfg.proc_sigma * rng_arr.standard_normal(n))

    offs = attempt_offsets(cfg)
    pending = np.ones(n, bool)
    done_t = np.full(n, np.nan)       # completion time
    att_ok = np.zeros(n, np.int8)     # attempt number that succeeded (1-based), 0 = failed
    path_ok = np.zeros(n, np.int8)
    net_ok = np.full(n, np.nan)       # d_up + d_down of the successful attempt
    qwait = np.full(n, np.nan)
    sent_msgs = np.zeros(n, np.int16)   # messages put on a path (requests + responses)
    lost_msgs = np.zeros(n, np.int16)   # of which lost
    nopath = np.zeros(n, np.int16)      # attempts made while no path was usable
    qhist = {}                        # path -> (up_arrivals, up_waits, dn_arrivals, dn_waits)

    for k, off in enumerate(offs):
        idx = np.nonzero(pending)[0]
        if idx.size == 0:
            break
        rng = np.random.default_rng(seed_seq + [100 + k])
        # draws for both paths, for ALL transactions (keeps CRN exact)
        U = {p: rng.uniform(-1, 1, (n, 2)) for p in "AB"}
        Rl = {p: rng.random((n, 2)) for p in "AB"}
        t_send = arr[idx] + off
        sel = monitor.sel_at(t_send)
        nopath[idx[sel == 0]] += 1
        for p, pi in (("A", 1), ("B", 2)):
            m = idx[sel == pi]
            if m.size == 0:
                continue
            ts = arr[m] + off
            s = cfg.service_time_s(p)
            d, j, l = cond.params(p, ts)
            if k == 0:
                order = np.argsort(ts, kind="stable")
                w = np.empty(m.size); w[order] = lindley_waits(ts[order], s)
                up_arr_sorted, up_w_sorted = ts[order], w[order]
            elif p in qhist:
                w = virtual_wait(qhist[p][0], qhist[p][1], s, ts)
            else:
                w = np.zeros(m.size)
            d_up = d + j * U[p][m, 0] + w + s
            lost_up = Rl[p][m, 0] < l
            t_srv = ts + d_up + proc[m]
            d2, j2, l2 = cond.params(p, t_srv)
            reach = ~lost_up
            w2 = np.zeros(m.size)
            if k == 0:
                rr = np.nonzero(reach)[0]
                o2 = rr[np.argsort(t_srv[rr], kind="stable")]
                w2[o2] = lindley_waits(t_srv[o2], s)
                qhist[p] = (up_arr_sorted, up_w_sorted, t_srv[o2], w2[o2])
            elif p in qhist:
                da, dw = qhist[p][2], qhist[p][3]
                w2 = virtual_wait(da, dw, s, t_srv)
            d_dn = d2 + j2 * U[p][m, 1] + w2 + s
            lost_dn = reach & (Rl[p][m, 1] < l2)
            ok = reach & ~lost_dn
            t_done = t_srv + d_dn
            ok &= (t_done - arr[m]) <= cfg.timeout_s
            sent_msgs[m] += 1 + reach
            lost_msgs[m] += lost_up.astype(np.int16) + lost_dn.astype(np.int16)
            if k == 0 and p not in qhist:
                qhist[p] = (up_arr_sorted, up_w_sorted, np.array([]), np.array([]))
            g = m[ok]
            done_t[g] = t_done[ok]
            att_ok[g] = k + 1
            path_ok[g] = pi
            net_ok[g] = (d_up + d_dn)[ok]
            qwait[g] = (w + w2)[ok]
            pending[g] = False
    success = att_ok > 0
    rt = np.where(success, done_t - arr, np.nan)
    retx_wait = np.where(success, offs[np.maximum(att_ok - 1, 0)], np.nan)
    return {
        "arr": arr, "proc": proc, "success": success, "rt": rt, "done": done_t,
        "attempt": att_ok, "path": path_ok, "net": net_ok, "qwait": qwait,
        "retx_wait": retx_wait, "sent_msgs": sent_msgs, "lost_msgs": lost_msgs, "nopath": nopath,
    }
