# Ceph-P4-Booster — BMv2/Mininet Emulation Artifact

Emulation code, measurement data, and plotting scripts for the paper:

> **Ceph-P4-Booster: In-Network Commit Decisions for Low-Latency Replicated Writes**
> F. Lei, Y. Wang, J. Chen, F. Zhou, Y. Liang, and Q. He.
> Submitted to *IEEE Transactions on Cloud Computing*.

This repository covers **Section VI-D** of the paper — the four emulation
experiments that reach load and concurrency regimes the three-node testbed
cannot. The real-cluster results (Sections VI-A to VI-C) were obtained on a
production Ceph deployment with an Intel Tofino switch and are not reproducible
outside that environment; the numbers are reported in the paper.

---

## What maps to what

| Paper | Experiment | Command | Data file |
|---|---|---|---|
| Fig. 10, Table XIII | Load sweep, 50–600 req/s, Poisson | `run_calibrated_extra.py sweep` | `figures/data/sim_load_sweep.csv` |
| Fig. 11 | Latency distribution at 100 and 450 req/s | `run_calibrated_extra.py cdf` | `figures/data/sim_cdf_*.txt` |
| Fig. 12, Table XIV | Stepped load 150→300→450→550→300→150 | `run_calibrated_extra.py timeline` | `figures/data/sim_timeline_*.csv` |
| Fig. 13, Table XV | Throughput vs. 1–16 concurrent clients | `run_calibrated_extra.py scal` | `figures/data/sim_scalability.csv` |

`figures/data/floor_*_ms.txt` hold the emulation floor measured separately for
each group. `figures/data/hw_*_latency_us.txt` are the 1000 per-sample latencies
measured on the real cluster; they are the distribution the emulator samples its
wait times from, and the reference the model is aligned against in Section VI-D-1.

---

## Layout

```
p4/                     BMv2 data plane
  booster.p4              completion-event aggregation
  booster.json            compiled by p4c (v1model)
  rules.txt               forwarding and aggregation table entries
emulation/
  run_calibrated_extra.py main entry point for the four experiments
  h2_server.py            endpoint model: service time and wait time separated
  h1_client_ext.py        open-loop / closed-loop load generator
  run_calibrated_load.py  first-round load sweep (fixed-interval arrivals)
  h1_client.py            open-loop client used by run_calibrated_load.py
  predict.py              offline M/D/1 check — parameter selection only,
                          never a source of reported results
  inputs/                 per-sample wait times sampled from the real cluster
figures/
  make_figures.py         Fig. 9-13   (data plots)
  make_schematics.py      Fig. 1-8    (schematics)
  figstyle.py figkit.py   shared palette, fonts, layout audit
  data/                   the measurement data behind every figure
docs/
  experiment-protocol.md  the run sheet actually used, with expected output
  calibration-notes.md    how the model was calibrated, and what failed
```

---

## Requirements

The emulation runs inside the [p4lang tutorials](https://github.com/p4lang/tutorials)
VM (Ubuntu 20.04) or an equivalent setup providing:

- Mininet, with `p4_mininet` on the Python path
- BMv2 `simple_switch`, and `simple_switch_CLI` for table entries
- `p4c` with the `v1model` architecture (only needed to rebuild `booster.json`)
- Python 3.8+

Plotting is independent of the above and needs only Python 3.8+ with
`matplotlib` and `numpy`.

---

## Running

```bash
# from the emulation/ directory, with p4/ contents alongside
sudo mn -c
sudo python3 run_calibrated_extra.py --check      # client capability self-test
sudo python3 run_calibrated_extra.py scal         # ~8 min
sudo python3 run_calibrated_extra.py cdf          # ~4 min
sudo python3 run_calibrated_extra.py timeline     # ~6 min
sudo python3 run_calibrated_extra.py sweep        # ~6 min
```

Each group ends with a sanity check comparing the smallest measured latency
against the minimum of the sampled wait distribution. A result below that
minimum is physically impossible and is reported as a failure — stop and
investigate rather than using the data. `docs/calibration-notes.md` records the
one occasion this check caught a real bug.

Regenerating the figures:

```bash
cd figures
python3 make_figures.py        # Fig. 9-13
python3 make_schematics.py     # Fig. 1-8
```

Both write PDF and PNG under `figures/out/`, in Chinese and English.

---

## Three things the paper states explicitly, repeated here

**The service time is a model parameter, not a measurement.** `SVC_B = 2.0 ms`
and `SVC_O = 0.5 ms` set the capacity of the two paths to about 500 and
2000 req/s. They are deliberately larger than the per-request overhead of the
Python interpreter (0.3–1 ms); otherwise the knee of the curve would be set by
the interpreter rather than by the model. Their absolute values are not claimed
to be measured.

**Arrivals are Poisson.** This matches the M/G/1 assumption of the
Pollaczek–Khinchine analysis in Section III, so the emulated curves and the
analysis check each other rather than talking past each other. An earlier
fixed-interval version produced a flat curve before the knee — an artifact of
perfectly paced arrivals, not the shape of a real system.

**The emulation floor is measured per group, never reused across groups.** It is
the intrinsic cost of veth, the BMv2 round trip, and the interpreter, and it is
not stable between Mininet instances. Each figure is annotated with the floor
measured for that group.

---

## Not included

- The Tofino data-plane program and the Gate implementation that run on the
  production cluster. Sections VI-A to VI-C report measurements from that
  deployment; the code is outside the scope of this artifact.
- Superseded experiment runs, and one batch of data discarded for a measurement
  bias documented in `docs/calibration-notes.md`.

---

## License

MIT — see [LICENSE](LICENSE).

If this artifact is useful in your work, a citation of the paper is appreciated.
