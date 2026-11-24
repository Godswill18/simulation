"""
network.py - WAN path conditions, per-message delay/loss, and link queueing.

One-way network delay of a message on path p sent at time t:

    d = D_p(t) + J_p(t) * u  +  w_q  +  s_p              u ~ Uniform(-1, 1)

  D_p(t)  base one-way delay of the profile active at t (Table 10)
  J_p(t)  jitter half-width (NETem-style uniform variation)
  w_q     waiting time in the FIFO queue of the access link (Lindley recursion)
  s_p     serialisation (service) time = wire bytes * 8 / link rate

A message is lost with probability L_p(t) (per direction). In a blackout
L_p(t) = 1, i.e. nothing gets through.
"""
import numpy as np
from .config import P0_A, P0_B, P1, P2

PATH_INDEX = {"A": 1, "B": 2}      # 0 is used for "no path"


class Conditions:
    """Ground-truth state of every path over time for one run."""

    def __init__(self, cfg, condition):
        self.cfg = cfg
        self.condition = condition              # "steady" | "brownout" | "blackout"
        self.fault = {"steady": None, "brownout": P1, "blackout": P2}[condition]

    def in_fault(self, t):
        t = np.asarray(t, float)
        if self.fault is None:
            return np.zeros(t.shape, bool)
        return (t >= self.cfg.fault_on) & (t < self.cfg.fault_off)

    def params(self, path, t):
        """Return (delay_s, jitter_s, loss) arrays for path 'A'/'B' at times t."""
        t = np.asarray(t, float)
        base = P0_A if path == "A" else P0_B
        d = np.full(t.shape, base.delay_ms / 1000.0)
        j = np.full(t.shape, base.jitter_ms / 1000.0)
        l = np.full(t.shape, base.loss)
        if path == "A" and self.fault is not None:
            m = self.in_fault(t)
            d[m] = self.fault.delay_ms / 1000.0
            j[m] = self.fault.jitter_ms / 1000.0
            l[m] = self.fault.loss
        return d, j, l

    def link_up(self, path, t):
        """Ground truth: does the path deliver anything at time t?"""
        _, _, l = self.params(path, t)
        return l < 1.0

    def sla_compliant_truth(self, path, t):
        """Ground truth: would the path meet the SLA thresholds at time t?
        RTT = 2 x one-way delay; RTT jitter of two uniform +/-J variations has
        mean absolute successive difference ~0.933 J (numerically, 10^6 samples); loss compounds
        over two directions."""
        d, j, l = self.params(path, t)
        cfg = self.cfg
        rtt_ms = 2 * d * 1000
        jit_ms = 0.933 * j * 1000
        loss_pct = (1 - (1 - l) ** 2) * 100
        return (l < 1) & (rtt_ms <= cfg.sla_latency_ms) & (jit_ms <= cfg.sla_jitter_ms) & (loss_pct <= cfg.sla_loss_pct)


def lindley_waits(arrivals, service):
    """Exact FIFO waiting times for messages arriving at sorted times
    `arrivals` to a single server with constant service time `service`.

        W_1 = 0,   W_n = max(0, W_{n-1} + s - (a_n - a_{n-1}))

    Vectorised with the closed form W_n = C_n - min(0, min_{k<=n} C_k),
    C_n = sum_{k<=n} (s - tau_k)."""
    a = np.asarray(arrivals, float)
    if a.size == 0:
        return a.copy()
    x = np.empty_like(a)
    x[0] = 0.0
    x[1:] = service - np.diff(a)
    c = np.cumsum(x)
    return c - np.minimum(0.0, np.minimum.accumulate(c))


def virtual_wait(arrivals, waits, service, t):
    """Waiting time a message arriving at arbitrary time t would see, given the
    queue history (arrivals, waits) of the regular traffic:
        V(t) = max(0, W_n + s - (t - a_n)),  a_n = last arrival before t."""
    t = np.asarray(t, float)
    if len(arrivals) == 0:
        return np.zeros(t.shape)
    i = np.searchsorted(arrivals, t, side="right") - 1
    v = np.zeros(t.shape)
    ok = i >= 0
    v[ok] = np.maximum(0.0, waits[i[ok]] + service - (t[ok] - arrivals[i[ok]]))
    return v


def probe_queue_sample(rho, rng, service, size):
    """Queueing delay seen by a monitoring probe on a link loaded to utilisation
    rho (heavy-traffic approximation of the M/D/1 waiting time):
    with probability rho the probe waits, and the wait is exponential with mean
    W/rho, where W = rho * s / (2 (1 - rho)) is the M/D/1 mean wait."""
    rho = np.clip(np.asarray(rho, float), 0.0, 0.98)
    w_mean = rho * service / (2.0 * (1.0 - rho))
    busy = rng.random(size) < rho
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(rho > 0, w_mean / np.maximum(rho, 1e-12), 0.0)
    return np.where(busy, rng.exponential(1.0, size) * scale, 0.0)
