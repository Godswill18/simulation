"""
monitor.py - path monitoring and the two path-selection policies.

Both policies produce a selection timeline sel[k] on a 0.2 s grid:
0 = no usable path, 1 = Path A, 2 = Path B. A transaction (or retransmission)
sent at time t uses the path selected at the last grid point <= t.

STATIC PATH SELECTION (baseline)
  Primary = Path A, backup = Path B. A reachability tracker probes each path
  every 1 s. A path is declared DOWN after 3 consecutive lost probes and UP
  after 3 consecutive answered probes. Traffic uses A while A is UP, otherwise
  B while B is UP. Latency, jitter and loss are NOT considered, so a degraded
  but reachable primary keeps the traffic.

DYNAMIC PATH SELECTION (SLA-based, FortiGate-like)
  Every path is probed every 0.2 s. For each path:
    latency  = mean RTT of the answered probes among the last 30 probes
    jitter   = mean |RTT_i - RTT_(i-1)| of consecutive answered probes in the last 30
    loss %   = lost probes / last 100 probes * 100
    liveness = DEAD after 5 consecutive lost probes, ALIVE after 10 consecutive answered
    in SLA   = ALIVE and latency <= 60 ms and jitter <= 10 ms and loss <= 1 %
  Selection in priority order A, B: the first path in SLA; if none is in SLA,
  the first ALIVE path; if none is alive, no path.
  Optional hold-down (dps_holddown_s): while on B, return to A only after A
  has been in SLA continuously for the hold-down time (prevents flapping).
  Switching is therefore not instantaneous: a probe's result is only known when
  its reply arrives (one RTT) or, if it is lost, when the probe timeout expires
  (0.5 s DPS, 1 s static); the averaging windows and liveness counters must then
  cross their thresholds.
"""
import heapq
from collections import deque
import numpy as np
from .network import probe_queue_sample

GRID = 0.2


def grid_times(cfg):
    start = -cfg.preroll_s
    end = cfg.total_s + cfg.timeout_s + 2.0
    n = int(round((end - start) / GRID)) + 1
    return start + GRID * np.arange(n)


def _probe_rtts(cfg, cond, path, times, rng, rho_loaded, timeout):
    """Pre-draw probe outcomes at `times` for the unloaded and loaded cases."""
    n = len(times)
    d, j, l = cond.params(path, times)
    u1, u2 = rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)
    r1, r2 = rng.random(n), rng.random(n)
    s = cfg.service_time_s(path)
    q1 = probe_queue_sample(rho_loaded, rng, s, n)
    q2 = probe_queue_sample(rho_loaded, rng, s, n)
    base = 2 * d + j * (u1 + u2)
    rtt_unloaded = base
    rtt_loaded = base + q1 + q2
    lost = (r1 < l) | (r2 < l)
    lost_u = lost | (rtt_unloaded > timeout)
    lost_l = lost | (rtt_loaded > timeout)
    return rtt_unloaded, rtt_loaded, lost_u, lost_l


class MonitorResult:
    def __init__(self, times, sel, log=None, events=None):
        self.times, self.sel, self.log, self.events = times, sel, log or {}, events or []

    def sel_at(self, t):
        k = np.floor((np.asarray(t, float) - self.times[0]) / GRID + 1e-9).astype(int)
        k = np.clip(k, 0, len(self.sel) - 1)
        return self.sel[k]


def _apply_delay(cfg, sel):
    """Traffic follows a decision only after policy_update_delay_s."""
    d = int(round(cfg.policy_update_delay_s / GRID))
    if d <= 0:
        return sel
    out = sel.copy()
    out[d:] = sel[:-d]
    return out


def _events(times, sel, branch, policy):
    ev = []
    for k in range(1, len(sel)):
        if sel[k] != sel[k - 1]:
            ev.append({"t": float(times[k]), "branch": branch, "policy": policy,
                       "from": int(sel[k - 1]), "to": int(sel[k])})
    return ev


def run_dps(cfg, cond, load_tps, rng, branch):
    times = grid_times(cfg)
    n = len(times)
    pre = {}
    for p in ("A", "B"):
        rho = load_tps / cfg.capacity_msgs(p)
        pre[p] = _probe_rtts(cfg, cond, p, times, rng, rho, cfg.dps_probe_timeout_s)
    win_l = {p: deque(maxlen=cfg.dps_latency_window) for p in "AB"}   # (lost, rtt)
    win_p = {p: deque(maxlen=cfg.dps_loss_window) for p in "AB"}      # lost flags
    alive = {p: True for p in "AB"}
    consec_lost = {p: 0 for p in "AB"}
    consec_ok = {p: 0 for p in "AB"}
    state = {p: (0.0, 0.0, 0.0, True, True) for p in "AB"}            # lat, jit, loss, alive, in_sla
    pending = []                                                       # heap of (known_time, seq, path, lost, rtt)
    sel = np.zeros(n, np.int8)
    log = {f"{k}_{p}": np.full(n, np.nan) for k in ("rtt", "lat", "jit", "loss", "alive", "sla") for p in "AB"}
    current = 1
    a_ok_since = times[0]
    seq = 0
    for k in range(n):
        t = times[k]
        # 1. send this tick's probes; a result is known when the reply arrives,
        #    or when the probe timeout expires if no reply comes
        for p, idx in (("A", 1), ("B", 2)):
            ru, rl, lu, ll = pre[p]
            loaded = current == idx
            rtt = rl[k] if loaded else ru[k]
            lost = ll[k] if loaded else lu[k]
            known = t + (cfg.dps_probe_timeout_s if lost else rtt)
            heapq.heappush(pending, (known, seq, p, bool(lost), float(rtt))); seq += 1
            log[f"rtt_{p}"][k] = np.nan if lost else 1000 * rtt
        # 2. process every result that has become known by time t
        changed = set()
        while pending and pending[0][0] <= t + 1e-12:
            _, _, p, lost, rtt = heapq.heappop(pending)
            win_l[p].append((lost, rtt)); win_p[p].append(lost); changed.add(p)
            if lost:
                consec_lost[p] += 1; consec_ok[p] = 0
            else:
                consec_ok[p] += 1; consec_lost[p] = 0
            if alive[p] and consec_lost[p] >= cfg.dps_failtime:
                alive[p] = False
            elif not alive[p] and consec_ok[p] >= cfg.dps_recoverytime:
                alive[p] = True
        # 3. SLA evaluation per path
        for p in changed:
            good = [r for (lo, r) in win_l[p] if not lo]
            lat = 1000 * sum(good) / len(good) if good else np.inf
            sq = list(win_l[p])
            diffs = [abs(sq[i][1] - sq[i - 1][1]) for i in range(1, len(sq)) if not sq[i][0] and not sq[i - 1][0]]
            jit = 1000 * sum(diffs) / len(diffs) if diffs else (0.0 if good else np.inf)
            loss = 100.0 * sum(win_p[p]) / len(win_p[p])
            in_sla = alive[p] and lat <= cfg.sla_latency_ms and jit <= cfg.sla_jitter_ms and loss <= cfg.sla_loss_pct
            state[p] = (lat, jit, loss, alive[p], in_sla)
        ok = {}
        for p in "AB":
            lat, jit, loss, al, in_sla = state[p]
            ok[p] = in_sla
            log[f"lat_{p}"][k], log[f"jit_{p}"][k], log[f"loss_{p}"][k] = lat, jit, loss
            log[f"alive_{p}"][k], log[f"sla_{p}"][k] = al, in_sla
        # 4. selection (priority A then B, optional hold-down)
        if not ok["A"]:
            a_ok_since = None
        elif a_ok_since is None:
            a_ok_since = t
        held = (current == 2 and ok["A"] and ok["B"] and cfg.dps_holddown_s > 0
                and t - a_ok_since < cfg.dps_holddown_s)
        if ok["A"] and not held:
            current = 1
        elif ok["B"]:
            current = 2
        elif alive["A"]:
            current = 1
        elif alive["B"]:
            current = 2
        else:
            current = 0
        sel[k] = current
    sel = _apply_delay(cfg, sel)
    return MonitorResult(times, sel, log, _events(times, sel, branch, "dps"))


def run_static(cfg, cond, load_tps, rng, branch):
    times = grid_times(cfg)
    n = len(times)
    step = int(round(cfg.static_probe_interval_s / GRID))
    ptimes = times[::step]
    pre = {}
    for p in ("A", "B"):
        rho = load_tps / cfg.capacity_msgs(p)
        pre[p] = _probe_rtts(cfg, cond, p, ptimes, rng, rho, cfg.static_probe_timeout_s)
    up = {p: True for p in "AB"}
    cl = {p: 0 for p in "AB"}
    co = {p: 0 for p in "AB"}
    sel = np.zeros(n, np.int8)
    pending, seq, current = [], 0, 1
    for k in range(n):
        t = times[k]
        if k % step == 0:
            i = k // step
            for p, idx in (("A", 1), ("B", 2)):
                ru, rl, lu, ll = pre[p]
                lost = ll[i] if current == idx else lu[i]
                rtt = rl[i] if current == idx else ru[i]
                known = t + (cfg.static_probe_timeout_s if lost else rtt)
                heapq.heappush(pending, (known, seq, p, bool(lost))); seq += 1
        while pending and pending[0][0] <= t + 1e-12:
            _, _, p, lost = heapq.heappop(pending)
            if lost:
                cl[p] += 1; co[p] = 0
            else:
                co[p] += 1; cl[p] = 0
            if up[p] and cl[p] >= cfg.static_down_after:
                up[p] = False
            elif not up[p] and co[p] >= cfg.static_up_after:
                up[p] = True
        backup = up["B"] and cfg.static_backup_enabled
        current = 1 if up["A"] else (2 if backup else 0)
        sel[k] = current
    sel = _apply_delay(cfg, sel)
    return MonitorResult(times, sel, {}, _events(times, sel, branch, "static"))
