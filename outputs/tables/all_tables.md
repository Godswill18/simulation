# Python model-based simulation results (not real-world measurements)

## design

| treatment | load_tps | condition_group | condition | runs |
|---|---|---|---|---|
| dps | 50 | impairment-event | blackout | 2 |
| dps | 50 | impairment-event | brownout | 3 |
| dps | 50 | steady-state | steady | 5 |
| dps | 150 | impairment-event | blackout | 2 |
| dps | 150 | impairment-event | brownout | 3 |
| dps | 150 | steady-state | steady | 5 |
| dps | 300 | impairment-event | blackout | 2 |
| dps | 300 | impairment-event | brownout | 3 |
| dps | 300 | steady-state | steady | 5 |
| dps | 450 | impairment-event | blackout | 2 |
| dps | 450 | impairment-event | brownout | 3 |
| dps | 450 | steady-state | steady | 5 |
| static | 50 | impairment-event | blackout | 2 |
| static | 50 | impairment-event | brownout | 3 |
| static | 50 | steady-state | steady | 5 |
| static | 150 | impairment-event | blackout | 2 |
| static | 150 | impairment-event | brownout | 3 |
| static | 150 | steady-state | steady | 5 |
| static | 300 | impairment-event | blackout | 2 |
| static | 300 | impairment-event | brownout | 3 |
| static | 300 | steady-state | steady | 5 |
| static | 450 | impairment-event | blackout | 2 |
| static | 450 | impairment-event | brownout | 3 |
| static | 450 | steady-state | steady | 5 |

## response_time_by_load

| Condition | Load (tps) | Static mean | Static p95 | Static p99 | Dynamic mean | Dynamic p95 | Dynamic p99 |
|---|---|---|---|---|---|---|---|
| steady | 50 | 28.74 | 33.61 | 37.25 | 28.74 | 33.61 | 37.25 |
| steady | 150 | 29.32 | 34.62 | 38.36 | 29.32 | 34.62 | 38.36 |
| steady | 300 | 31.01 | 38.01 | 42.52 | 31.01 | 38.01 | 42.52 |
| steady | 450 | 40.19 | 61.13 | 76.26 | 47.04 | 61.17 | 69.11 |
| brownout | 50 | 54.61 | 127.66 | 336.50 | 37.68 | 59.10 | 64.04 |
| brownout | 150 | 55.23 | 128.31 | 338.57 | 37.94 | 59.11 | 64.50 |
| brownout | 300 | 57.06 | 130.52 | 340.61 | 39.03 | 59.08 | 63.87 |
| brownout | 450 | 66.54 | 143.36 | 349.67 | 49.60 | 61.34 | 67.82 |
| blackout | 50 | 53.55 | 58.97 | 65.27 | 38.92 | 59.03 | 62.99 |
| blackout | 150 | 53.30 | 58.90 | 65.14 | 39.38 | 59.00 | 63.05 |
| blackout | 300 | 54.71 | 59.01 | 65.15 | 40.50 | 59.10 | 63.11 |
| blackout | 450 | 61.38 | 62.71 | 86.74 | 50.52 | 61.40 | 67.86 |

## rt_components

| Condition | Policy | Mean RT (ms) | Network delay (ms) | Application processing (ms) | Retransmission wait (ms) |
|---|---|---|---|---|---|
| steady | Static | 32.32 | 27.78 | 4.53 | 0.000 |
| steady | Dynamic | 34.03 | 29.50 | 4.53 | 0.000 |
| brownout | Static | 58.36 | 50.75 | 4.53 | 3.076 |
| brownout | Dynamic | 41.06 | 36.48 | 4.53 | 0.046 |
| blackout | Static | 55.73 | 34.62 | 4.53 | 16.581 |
| blackout | Dynamic | 42.33 | 36.68 | 4.53 | 1.114 |

## availability

| Condition | Policy | Runs | WAN link avail. Path A (%) | Service avail. (%) | SLA-compliant time (%) | Transaction avail. (%) | Fault-window service avail. (%) | Fault-window SLA-compliant (%) | Fault-window txn avail. (%) | Failed txns (mean/run) |
|---|---|---|---|---|---|---|---|---|---|---|
| steady | Static | 20 | 100.000 | 100.000 | 100.000 | 100.0000 | n/a | n/a | n/a | 0.0 |
| steady | Dynamic | 20 | 100.000 | 100.000 | 100.000 | 100.0000 | n/a | n/a | n/a | 0.0 |
| brownout | Static | 12 | 100.000 | 100.000 | 71.429 | 100.0000 | 100.000 | 0.000 | 100.0000 | 0.0 |
| brownout | Dynamic | 12 | 100.000 | 100.000 | 99.603 | 100.0000 | 100.000 | 98.611 | 100.0000 | 0.0 |
| blackout | Static | 8 | 71.429 | 99.286 | 99.286 | 100.0000 | 97.500 | 97.500 | 100.0000 | 0.0 |
| blackout | Dynamic | 8 | 71.429 | 99.835 | 99.835 | 100.0000 | 99.424 | 99.424 | 100.0000 | 0.0 |

## failover

| Condition | Load (tps) | Policy | Failover time (s) | Branches on B at onset | Recovery time (s) | Fail-back time (s) | Longest outage (s) | Fault-window p95 RT (ms) | Fault-window on Path B (%) |
|---|---|---|---|---|---|---|---|---|---|
| brownout | 50 | Static | n/a | 0.0 | n/a | n/a | 0.19 | 143.22 | 0.0 |
| brownout | 50 | Dynamic | 2.13 | 0.0 | 2.21 | 16.13 | 0.19 | 62.31 | 98.2 |
| brownout | 150 | Static | n/a | 0.0 | n/a | n/a | 0.07 | 144.34 | 0.0 |
| brownout | 150 | Dynamic | 2.47 | 0.0 | 2.52 | 12.47 | 0.07 | 62.62 | 97.9 |
| brownout | 300 | Static | n/a | 0.0 | n/a | n/a | 0.05 | 146.89 | 0.0 |
| brownout | 300 | Dynamic | 1.87 | 0.0 | 1.92 | 12.07 | 0.05 | 62.35 | 98.4 |
| brownout | 450 | Static | n/a | 0.0 | n/a | n/a | 0.03 | 171.67 | 0.0 |
| brownout | 450 | Dynamic | 0.33 | 1.3 | 0.17 | 10.63 | 0.03 | 61.66 | 99.8 |
| blackout | 50 | Static | 3.00 | 0.0 | 3.06 | 2.20 | 3.05 | 63.00 | 100.0 |
| blackout | 50 | Dynamic | 0.80 | 0.0 | 0.86 | 20.00 | 0.86 | 61.74 | 100.0 |
| blackout | 150 | Static | 3.00 | 0.0 | 3.06 | 2.20 | 3.05 | 62.94 | 100.0 |
| blackout | 150 | Dynamic | 0.80 | 0.0 | 0.86 | 20.00 | 0.85 | 61.76 | 100.0 |
| blackout | 300 | Static | 3.00 | 0.0 | 3.05 | 2.20 | 3.04 | 63.00 | 100.0 |
| blackout | 300 | Dynamic | 0.80 | 0.0 | 0.86 | 20.00 | 0.85 | 61.82 | 100.0 |
| blackout | 450 | Static | 3.00 | 0.0 | 3.05 | 2.20 | 3.04 | 63.05 | 100.0 |
| blackout | 450 | Dynamic | 0.70 | 2.0 | 0.00 | 20.00 | 0.41 | 61.71 | 100.0 |

## network

| Condition | Window | Policy | Latency, mean RTT (ms) | Jitter (ms) | Message loss (%) | Throughput (tps) | Retransmitted txns (%) | Path switches / branch-hour |
|---|---|---|---|---|---|---|---|---|
| steady | measurement | Static | 27.78 | 1.62 | 0.000 | 712.4 | 0.000 | 0.0 |
| steady | measurement | Dynamic | 29.50 | 1.70 | 0.000 | 712.4 | 0.000 | 574.3 |
| brownout | fault | Static | 108.30 | 18.85 | 2.003 | 712.2 | 3.965 | 0.0 |
| brownout | fault | Dynamic | 51.84 | 3.04 | 0.031 | 712.2 | 0.059 | 392.1 |
| blackout | fault | Static | 51.07 | 2.80 | 3.732 | 711.3 | 2.518 | 17.1 |
| blackout | fault | Dynamic | 51.07 | 2.80 | 0.491 | 711.3 | 0.570 | 398.2 |

## tests_confirmatory

| Hypothesis | Metric | Condition | Pairs | Mean static | Mean dynamic | Median diff (S-D) | Wilcoxon p (Holm) | Sign-test p | r_rb | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| H01 | 95th percentile response time (ms) | steady | 20 | 41.84 | 41.85 | 0.000 | 1.000 | 1.000 | -0.07 |  |
| H01 | 95th percentile response time (ms) | brownout | 12 | 132.46 | 59.66 | 70.356 | 0.003 | <0.001 | 1.00 |  |
| H01 | 95th percentile response time (ms) | blackout | 8 | 59.90 | 59.63 | -0.081 | 1.000 | 0.289 | -0.17 |  |
| H02 | Transaction availability (%) [fault window] | brownout | 12 | 100.00 | 100.00 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H02 | End-to-end service availability (%) [fault window] | brownout | 12 | 100.00 | 100.00 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H02 | SLA-compliant service time (%) [fault window] | brownout | 12 | 0.00 | 98.61 | -98.250 | 0.003 | <0.001 | -1.00 |  |
| H02 | Transaction availability (%) [fault window] | blackout | 8 | 100.00 | 100.00 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H02 | End-to-end service availability (%) [fault window] | blackout | 8 | 97.50 | 99.42 | -1.833 | 0.031 | 0.008 | -1.00 |  |
| H02 | SLA-compliant service time (%) [fault window] | blackout | 8 | 97.50 | 99.42 | -1.833 | 0.031 | 0.008 | -1.00 |  |

## tests_H03

| Hypothesis | Metric | Condition | Pairs | Mean static | Mean dynamic | Median diff (S-D) | Wilcoxon p (Holm) | Sign-test p | r_rb | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| H03 | Network latency, mean RTT (ms) | steady | 20 | 27.78 | 29.50 | 0.000 | 0.172 | 0.062 | -1.00 |  |
| H03 | Jitter (ms) | steady | 20 | 1.62 | 1.70 | 0.000 | 0.172 | 0.062 | -1.00 |  |
| H03 | Message loss (%) | steady | 20 | 0.00 | 0.00 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H03 | Throughput (successful tps, 3 branches) | steady | 20 | 712.44 | 712.44 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H03 | Network latency, mean RTT (ms) [fault window] | brownout | 12 | 108.30 | 51.84 | 53.710 | 0.004 | <0.001 | 1.00 |  |
| H03 | Jitter (ms) [fault window] | brownout | 12 | 18.85 | 3.04 | 15.677 | 0.004 | <0.001 | 1.00 |  |
| H03 | Message loss (%) [fault window] | brownout | 12 | 2.00 | 0.03 | 1.988 | 0.004 | <0.001 | 1.00 |  |
| H03 | Throughput (successful tps, 3 branches) [fault window] | brownout | 12 | 712.25 | 712.25 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H03 | Network latency, mean RTT (ms) [fault window] | blackout | 8 | 51.07 | 51.07 | 0.001 | 0.766 | 0.289 | 0.39 |  |
| H03 | Jitter (ms) [fault window] | blackout | 8 | 2.80 | 2.80 | -0.000 | 0.945 | 0.727 | 0.06 |  |
| H03 | Message loss (%) [fault window] | blackout | 8 | 3.73 | 0.49 | 3.169 | 0.047 | 0.008 | 1.00 |  |
| H03 | Throughput (successful tps, 3 branches) [fault window] | blackout | 8 | 711.28 | 711.28 | 0.000 | n/a | n/a | 0.00 | identical in every pair (no test) |
| H03 | Failover time (s) | blackout | 8 | 3.00 | 0.78 | 2.200 | 0.047 | 0.008 | 1.00 |  |

## hypothesis_decisions

| Hypothesis | Metric | Condition | Holm p | Decision |
|---|---|---|---|---|
| H01 | 95th percentile response time (ms) | steady | 1.000 | Fail to reject |
| H01 | 95th percentile response time (ms) | brownout | 0.003 | Reject |
| H01 | 95th percentile response time (ms) | blackout | 1.000 | Fail to reject |
| H02 | Transaction availability (%) [fault window] | brownout | n/a | Fail to reject (identical outcomes) |
| H02 | End-to-end service availability (%) [fault window] | brownout | n/a | Fail to reject (identical outcomes) |
| H02 | SLA-compliant service time (%) [fault window] | brownout | 0.003 | Reject |
| H02 | Transaction availability (%) [fault window] | blackout | n/a | Fail to reject (identical outcomes) |
| H02 | End-to-end service availability (%) [fault window] | blackout | 0.031 | Reject |
| H02 | SLA-compliant service time (%) [fault window] | blackout | 0.031 | Reject |
| H03 | Latency, jitter, loss, throughput (3 conditions), failover time (blackout) | all | 0.004 | Reject (5 of 13 metrics differ significantly) |

## sensitivity

| Scenario | Description | Policy | Condition | Load | Runs | Fault txn avail. (%) | Baseline | Fault svc avail. (%) | p95 RT (ms) | Baseline p95 | p99 RT (ms) | Failover (s) | Switches/run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_static_no_backup | Static single path with no backup (original Chapter 3 baseline) | Static | blackout | 300 | 5 | 4.639 | 100.000 | 0.00 | 40.02 | 59.01 | 7,778.28 | n/a | 6 |
| S1_static_no_backup | Static single path with no backup (original Chapter 3 baseline) | Static | brownout | 300 | 5 | 100.000 | 100.000 | 100.00 | 130.54 | 130.54 | 340.46 | n/a | 0 |
| S2_static_slow_detection | Static failover detection 5 s probes x 3 misses | Static | blackout | 300 | 5 | 97.286 | 100.000 | 90.83 | 59.75 | 59.01 | 3,810.26 | 11.00 | 6 |
| S3_policy_delay_1s | 1 s policy/route installation delay for both policies | Dynamic | blackout | 300 | 5 | 100.000 | 100.000 | 98.50 | 59.22 | 59.10 | 63.90 | 1.80 | 6 |
| S3_policy_delay_1s | 1 s policy/route installation delay for both policies | Dynamic | brownout | 300 | 5 | 100.000 | 100.000 | 100.00 | 59.20 | 59.08 | 65.12 | 2.96 | 6 |
| S3_policy_delay_1s | 1 s policy/route installation delay for both policies | Static | blackout | 300 | 5 | 100.000 | 100.000 | 96.67 | 59.14 | 59.01 | 69.95 | 4.00 | 6 |
| S3_policy_delay_1s | 1 s policy/route installation delay for both policies | Static | brownout | 300 | 5 | 100.000 | 100.000 | 100.00 | 130.54 | 130.54 | 340.46 | n/a | 0 |
| S4_timeout_2s | Stricter 2 s transaction timeout (terminal-style) | Dynamic | blackout | 300 | 5 | 100.000 | 100.000 | 99.33 | 59.10 | 59.10 | 63.10 | 0.80 | 6 |
| S4_timeout_2s | Stricter 2 s transaction timeout (terminal-style) | Dynamic | brownout | 300 | 5 | 100.000 | 100.000 | 100.00 | 59.06 | 59.08 | 63.82 | 1.84 | 6 |
| S4_timeout_2s | Stricter 2 s transaction timeout (terminal-style) | Static | blackout | 300 | 5 | 98.952 | 100.000 | 97.50 | 58.85 | 59.01 | 63.50 | 3.00 | 6 |
| S4_timeout_2s | Stricter 2 s transaction timeout (terminal-style) | Static | brownout | 300 | 5 | 100.000 | 100.000 | 100.00 | 130.54 | 130.54 | 340.45 | n/a | 0 |
| S5_dps_probe_window_10 | DPS latency/jitter window of 10 probes instead of 30 | Dynamic | brownout | 300 | 5 | 100.000 | 100.000 | 100.00 | 58.90 | 59.08 | 62.66 | 0.20 | 8 |
| S6_dps_holddown_20s | DPS hold-down of 20 s before returning to Path A | Dynamic | brownout | 450 | 5 | 100.000 | 100.000 | 100.00 | 61.54 | 61.36 | 65.79 | 0.53 | 65 |
| S6_dps_holddown_20s | DPS hold-down of 20 s before returning to Path A | Dynamic | steady | 450 | 5 | n/a | n/a | n/a | 61.52 | 61.17 | 66.01 | n/a | 94 |

