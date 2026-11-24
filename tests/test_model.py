"""
Validation tests for the simulation model. Run:  python -m pytest -q   (or python tests/test_model.py)
Each test checks one property the results depend on.
"""
import os, sys, dataclasses
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sdwan_sim.config import SimConfig
from sdwan_sim.network import lindley_waits, Conditions
from sdwan_sim.run import simulate_run
from sdwan_sim.transactions import attempt_offsets

CFG = SimConfig()


def test_lindley_matches_loop():
    rng = np.random.default_rng(0)
    a = np.cumsum(rng.exponential(1 / 450, 20000)); s = 0.002
    w_loop = np.zeros_like(a)
    for i in range(1, len(a)):
        w_loop[i] = max(0.0, w_loop[i - 1] + s - (a[i] - a[i - 1]))
    assert np.allclose(lindley_waits(a, s), w_loop)


def test_lindley_matches_md1_mean():
    rng = np.random.default_rng(1)
    lam, s = 450.0, 0.002; rho = lam * s
    a = np.cumsum(rng.exponential(1 / lam, 400000))
    w = lindley_waits(a, s)[20000:].mean()
    md1 = rho * s / (2 * (1 - rho))          # Pollaczek-Khinchine mean wait for M/D/1
    assert abs(w - md1) / md1 < 0.1, (w, md1)


def test_fault_schedule():
    c = Conditions(CFG, "blackout")
    assert not c.link_up("A", np.array([CFG.fault_on + 1]))[0]
    assert c.link_up("A", np.array([CFG.fault_on - 1]))[0]
    assert c.link_up("B", np.array([CFG.fault_on + 1]))[0]


def test_retransmission_schedule_inside_timeout():
    offs = attempt_offsets(CFG)
    assert offs[0] == 0 and offs[-1] < CFG.timeout_s
    assert np.allclose(offs[:4], [0, 0.25, 0.75, 1.75])


def test_common_random_numbers_steady_identical():
    """With no fault and no switching, both policies must give identical results."""
    a, _, _, _ = simulate_run(CFG, "static", 150, "steady", 1)
    b, _, _, _ = simulate_run(CFG, "dps", 150, "steady", 1)
    assert a["path_switches"] == 0 and b["path_switches"] == 0
    for k in ("attempted", "successful", "rt_p95_ms", "rt_mean_ms"):
        assert a[k] == b[k], k


def test_reproducible():
    a, _, _, _ = simulate_run(CFG, "dps", 50, "brownout", 2)
    b, _, _, _ = simulate_run(CFG, "dps", 50, "brownout", 2)
    assert a["rt_p95_ms"] == b["rt_p95_ms"] and a["failover_time_s_median"] == b["failover_time_s_median"]


def test_offered_load_and_availability_formula():
    s, _, _, _ = simulate_run(CFG, "static", 50, "steady", 3)
    expected = 50 * CFG.n_branches * CFG.measure_s
    assert abs(s["attempted"] - expected) / expected < 0.02
    assert s["txn_availability_pct"] == 100.0 * s["successful"] / s["attempted"]


def test_static_ignores_brownout_dps_reacts():
    st, _, _, _ = simulate_run(CFG, "static", 150, "brownout", 1)
    dp, _, _, _ = simulate_run(CFG, "dps", 150, "brownout", 1)
    assert st["fault_share_via_path_B_pct"] == 0.0
    assert dp["fault_share_via_path_B_pct"] > 90.0
    assert dp["failover_time_s_median"] > 0.5        # not instantaneous


def test_no_backup_loses_blackout_window():
    cfg = dataclasses.replace(CFG, static_backup_enabled=False)
    s, _, _, _ = simulate_run(cfg, "static", 50, "blackout", 4)
    assert s["fault_txn_availability_pct"] < 20.0


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f(); print("PASS", name)
