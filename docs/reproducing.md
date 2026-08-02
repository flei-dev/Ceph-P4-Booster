# Reproducing the Emulation Results

This covers Section VI-D of the paper: four experiment groups run on a
Mininet + BMv2 topology of one switch and three hosts. Total runtime is about
30 minutes. The groups are independent and can be run separately.

## Before starting

Everything runs from `emulation/`, with the contents of `p4/` alongside it:

```bash
cp ../p4/booster.json ../p4/rules.txt .
sudo mn -c
```

`booster.json` is the compiled artifact; rebuild it from source only if you need
to change the data plane:

```bash
p4c --target bmv2 --arch v1model -o . ../p4/booster.p4
```

The wait times in `emulation/inputs/` are 1000 per-sample latencies measured on
the real cluster — 17.336 ms median for the `size=3` baseline, 3.204 ms for the
proposed path. The emulator samples from these rather than generating a
hypothetical distribution, which is what lets Section VI-D-1 check the model
against measurement.

## Self-test first

```bash
sudo python3 run_calibrated_extra.py --check
```

This drives a pure-echo server with 16 closed-loop threads to measure the
throughput ceiling of the client itself. It must come out **well above
3000 ops/s**. The scalability experiment models a capacity of 2000 ops/s for the
proposed path; if the client can only push 1500, the high end of that curve is
bounded by Python rather than by the model, and the figure means nothing.

Stop here if the number is below 3000.

## The four groups

```bash
sudo python3 run_calibrated_extra.py scal        # ~8 min  -> Fig. 13, Table XV
sudo python3 run_calibrated_extra.py cdf         # ~4 min  -> Fig. 11
sudo python3 run_calibrated_extra.py timeline    # ~6 min  -> Fig. 12, Table XIV
sudo python3 run_calibrated_extra.py sweep       # ~6 min  -> Fig. 10, Table XIII
sudo python3 run_calibrated_extra.py all         # all four
```

**Scalability.** 1, 2, 3, 4, 6, 8, 10, 12, 16 concurrent clients, 12 s per point,
both modes. Closed loop, so no arrival process is involved. Both curves should
rise linearly and then flatten at their modeled capacities — around 500 ops/s for
the baseline and 2000 ops/s for the proposed path. A curve that flattens *before*
those values indicates the client is the limit, not the model.

**Latency distribution.** 100 and 450 req/s, 20 s per point. At 450 req/s the
baseline sits at 0.9 utilization while the proposed path is at 0.225; the
difference in headroom under the same offered load is the point of the figure.

**Time-varying load.** 150 → 300 → 450 → 550 → 300 → 150 req/s, 20 s per segment.
550 req/s exceeds the modeled capacity of the baseline but stays within that of
the proposed path, so one run shows the baseline entering overload, diverging, and
then recovering once the load steps back.

**Load sweep.** 50 to 600 req/s in steps of 50, 10 s per point.

## Reading the output

Each rate point prints `offered`, `recv`, and `achieved`. **`achieved` should
track the requested rate**; where it does not, the client failed to generate the
load and the point is not usable. The horizontal axis of Fig. 10 is achieved
load, not requested load.

Each group ends with a sanity check:

```
[健全性] baseline 实测最小 3.412 ms  采样分布最小 1.804 ms  本底 1.502 ms  通过
[健全性] booster  实测最小 2.088 ms  采样分布最小 1.873 ms  本底 1.502 ms  通过
```

The smallest measured latency cannot fall below the minimum of the sampled wait
distribution — that would be physically impossible. A `★ 不通过 ★` means the run
is invalid; stop and investigate rather than using the data. This check exists
because it caught a real defect: an earlier server revision estimated the
`time.sleep` overshoot at startup, when Mininet and BMv2 were still busy, and the
inflated estimate shifted an entire latency curve downward. The current revision
settles for 0.5 s first, takes the 20th percentile instead of the median, and
caps the correction at 0.5 ms.

Each group also measures its own emulation floor. The floor is the intrinsic cost
of veth, the BMv2 round trip, and the interpreter; it is not stable across Mininet
instances, so it is never reused between groups.

## Outputs

```
data_scalability_calibrated.csv
cdf_summary_calibrated.csv
lat_{baseline,booster}_{100,450}rps.txt
timeline_{baseline,booster}_calibrated.csv
floor_ms_timeline.txt
data_sweep_poisson.csv
floor_ms_poisson.txt
```

`figures/data/` holds the versions of these behind the figures in the paper, under
the names the plotting scripts expect. To plot a fresh run, copy the new files
over those, then:

```bash
cd ../figures && python3 make_figures.py
```

## Parameters

| | Value | Note |
|---|---|---|
| `SVC_B` | 2.0 ms | baseline service time, capacity ≈ 500 req/s |
| `SVC_O` | 0.5 ms | proposed path, capacity ≈ 2000 req/s |
| Arrivals | Poisson | matches the M/G/1 assumption of Section III |
| Topology | h1, h2, h3 — s1 | BMv2 `simple_switch`, thrift port 9090 |

The two service times are **model parameters, not measurements**. They are set
well above the per-request overhead of the Python interpreter (0.3–1 ms) so that
the knee of the curve is determined by the model rather than by the interpreter.
An earlier attempt at the values implied by the real cluster left the knee under
the interpreter's control and erased the fourfold capacity gap between the two
paths. The paper states this explicitly.
