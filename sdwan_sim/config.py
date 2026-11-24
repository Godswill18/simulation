"""
config.py - every parameter and assumption of the model in one place.

All values are MODEL ASSUMPTIONS for a simplified multi-branch banking network.
They are not measurements from any bank. Where a value follows the project's
Chapter 3 design (Tables 6, 9 and 10), that is stated next to it.

Units: seconds (s) unless a name ends in _ms; probabilities are 0..1.
"""
from dataclasses import dataclass, field, asdict
import json

MASTER_SEED = 2026          # documented seed; every run seed is derived from it


@dataclass(frozen=True)
class PathProfile:
    """Per-direction behaviour of one WAN path (one-way values)."""
    name: str
    delay_ms: float          # one-way base delay (propagation + provider network)
    jitter_ms: float         # half-width of a uniform +/- variation (as Linux NETem 'delay D J')
    loss: float              # per-direction message loss probability


# Table 10 of Chapter 3 (values per direction)
P0_A = PathProfile("P0-A normal Path A (MPLS-like)", 10.0, 1.0, 0.0)
P0_B = PathProfile("P0-B normal Path B (broadband)", 25.0, 3.0, 0.0)
P1 = PathProfile("P1 brownout on Path A", 50.0, 20.0, 0.02)
P2 = PathProfile("P2 blackout on Path A", 0.0, 0.0, 1.0)


@dataclass
class SimConfig:
    # ---------------- topology
    n_branches: int = 3                     # three branch sites + HQ data centre (Ch. 3.4.1)
    paths: tuple = ("A", "B")               # A = preferred private path, B = broadband

    # ---------------- traffic (Table 9) and transaction model
    loads_tps: tuple = (50, 150, 300, 450)  # offered transactions/s per branch
    arrival_process: str = "poisson"        # open-loop Poisson arrivals
    wire_bytes: int = 640                   # one message on the wire: 512 B payload + 2 B length
                                            # header + TCP/IP 40 B + IPsec ~72 B + Ethernet 14 B
    proc_median_ms: float = 4.0             # HQ application processing time, lognormal
    proc_sigma: float = 0.5                 #   (median 4 ms, mean ~4.5 ms); identical in both treatments
    timeout_s: float = 10.0                 # transaction fails if no response within 10 s
    rto_initial_s: float = 0.25             # transport retransmission timeout (TCP-like)
    rto_backoff: float = 2.0                # exponential back-off

    # ---------------- link capacity (rate caps, Ch. 3.6)
    # Path A is sized so the congested load (450 tps) loads it to 90 %:
    #   C_A = 450 / 0.9 messages/s = 500 msg/s = 500 * 640 * 8 bit/s = 2.56 Mbit/s per direction.
    # Path B has four times that, so it can carry the congested load inside the SLA (Ch. 3.6).
    capacity_mbps: dict = field(default_factory=lambda: {"A": 2.56, "B": 10.24})

    # ---------------- run protocol (Ch. 3.6)
    warmup_s: float = 60.0
    measure_s: float = 420.0
    fault_at_s: float = 180.0               # into the measurement period
    fault_duration_s: float = 120.0
    preroll_s: float = 30.0                 # monitors run before t=0 so their windows are full

    # ---------------- Dynamic Path Selection monitor (Table 6, Ch. 3.4.6)
    dps_probe_interval_s: float = 0.2
    dps_probe_timeout_s: float = 0.5
    dps_latency_window: int = 30            # latency and jitter averaged over last 30 probes
    dps_loss_window: int = 100              # loss % over last 100 probes
    dps_failtime: int = 5                   # consecutive lost probes -> path dead
    dps_recoverytime: int = 10              # consecutive good probes -> path alive again
    sla_latency_ms: float = 60.0
    sla_jitter_ms: float = 10.0
    sla_loss_pct: float = 1.0
    dps_holddown_s: float = 0.0             # return to the preferred path only after it has been
                                            # in SLA continuously this long (FortiOS hold-down-time,
                                            # default 0). 0 in the main design; 20 s in sensitivity S6.

    # ---------------- Static path selection with configured failover
    # Predetermined primary (A). A reachability tracker (like a floating static
    # route with IP SLA object tracking) moves traffic to B only when A stops
    # answering, and back when A answers again. It does not look at latency,
    # jitter or loss.
    static_probe_interval_s: float = 1.0
    static_probe_timeout_s: float = 1.0
    static_down_after: int = 3              # 3 consecutive lost probes -> primary down
    static_up_after: int = 3                # 3 consecutive good probes -> primary up
    static_backup_enabled: bool = True      # False = single path, no backup (original Ch. 3 baseline)

    # ---------------- both policies
    policy_update_delay_s: float = 0.0      # extra delay between a decision and traffic moving
                                            # (route/policy installation). 0 in the main design;
                                            # varied in the sensitivity analysis.

    # ---------------- design (Ch. 3.6)
    reps_steady: int = 5
    impairment_split: tuple = ("brownout", "brownout", "brownout", "blackout", "blackout")
    master_seed: int = MASTER_SEED

    # derived ---------------------------------------------------------
    @property
    def total_s(self):
        return self.warmup_s + self.measure_s

    @property
    def fault_on(self):
        return self.warmup_s + self.fault_at_s

    @property
    def fault_off(self):
        return self.fault_on + self.fault_duration_s

    def service_time_s(self, path):
        return self.wire_bytes * 8 / (self.capacity_mbps[path] * 1e6)

    def capacity_msgs(self, path):
        return 1.0 / self.service_time_s(path)

    def to_dict(self):
        d = asdict(self)
        d["derived"] = {
            "service_time_ms": {p: 1000 * self.service_time_s(p) for p in self.paths},
            "capacity_msgs_per_s": {p: self.capacity_msgs(p) for p in self.paths},
            "utilisation_path_A_at_loads": {L: L / self.capacity_msgs("A") for L in self.loads_tps},
            "fault_window_abs_s": [self.fault_on, self.fault_off],
            "measurement_window_abs_s": [self.warmup_s, self.total_s],
            "profiles": {p.name: asdict(p) for p in (P0_A, P0_B, P1, P2)},
        }
        return d

    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
