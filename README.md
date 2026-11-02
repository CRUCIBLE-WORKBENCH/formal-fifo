# Formal FIFO: counterexample, replay and safety proof

This demonstration finds a simultaneous-transfer occupancy bug in a four-entry, eight-bit synchronous FIFO, replays the solver's actual inputs in simulation, and proves the corrected implementation. **Crucible is beta.** The managed SymbiYosys bundle supplies the proof frontend and SMT dependencies; Icarus Verilog supplies an independent simulation route.

The reviewed [eleven-page PDF](docs/Formal_FIFO_Counterexample_and_Proof_Ignytion_A4.pdf) and [editable A4 PowerPoint](docs/Formal_FIFO_Counterexample_and_Proof_Ignytion_A4.pptx) explain the contract, counterexample and proof limits. [Recorded results](evidence/summary.json), [counterexample states](evidence/counterexample.csv) and [document hashes](evidence/documents.sha256.json) are included. Raw proof directories and logs are regenerated locally and ignored by Git.

## Recorded results and their scope

Measured locally on 1 November 2026:

| Check | Observed result |
|---|---|
| Preserved broken RTL | Occupancy assertion fails at formal step 4; SBY exits 2 |
| Corrected RTL safety | Basecase and temporal induction pass in `prove` mode |
| Reachability | All 12 cover statements reached, within 10 formal steps |
| Independent simulation | 2,195 cycles and 13,170 comparisons pass |
| Concrete witness replay | Corrected RTL passes five cycles and 30 comparisons |
| Broken simulation and replay | Both reject occupancy 2 when the reference expects 1; each exits 1 |

The proof establishes unbounded safety under the stated abstract single-clock/reset model for this exact fixed configuration. A depth of 16 supports induction; the result includes a successful induction step. It is not only a sixteen-cycle bounded check. Cover steps are abstract solver indices, not physical latency measurements.

## Interface and acceptance contract

`rtl/fifo.v` defines module `fifo`. Its inputs are `clk`, synchronous active-high `rst`, `wr_en`, eight-bit `wr_data` and `rd_en`. Outputs are eight-bit registered `rd_data`, registered `rd_valid`, `full`, `empty` and three-bit `level`.

Requests are accepted using occupancy **before** the rising edge: a write requires `wr_en && !full`, and a read requires `rd_en && !empty`.

| Pre-edge state | Both requests asserted | Result |
|---|---|---|
| Empty | Write accepted; read rejected | Occupancy becomes one; no valid read |
| Full | Read accepted; write rejected | Occupancy becomes three |
| Between empty and full | Both accepted | Oldest byte read; new byte appended; occupancy unchanged |

An accepted read asserts `rd_valid` and returns the oldest queued byte after the edge. Otherwise `rd_valid` is low and `rd_data` holds its previous value. Reset clears pointers, occupancy, valid and read data, discarding queued bytes. Unoccupied memory is not reset. There is no fall-through or full-through bypass.

The formal environment assumes reset on the first formal edge only. Later resets, requests and every data bit remain unconstrained. The shift-queue reference decides acceptance from its own count, independently of DUT flags. Pointer and occupied-memory relations are assertions proved with the safety properties, not assumptions that the DUT is correct.

## 1. Prerequisites, shell and directory

Use Linux x86-64 or WSL with an existing Crucible beta installation, Bash, Python 3 and Git. Run the Linux commands from this repository's root: the directory containing `crucible.toml`, `crucible.lock`, `rtl/`, `formal/`, `tests/` and `scripts/`. Open a WSL terminal for Bash commands. PowerShell commands below are labelled separately.

The lock pins `symbiyosys` 0.63.0 and `iverilog` 14.0.0 artifact packages. The observed proof bundle reports SBY `v0.63-11-g6424d15` and Yosys `0.63+188` (`cede13a74`). `scripts/verify.py` and `scripts/counterexample.py` use Python's standard library: no pip installation, PDK, board, vendor FPGA software or separate system solver is needed for the measured route. Acquisition on a new machine may download the pinned archives. Native Windows/macOS/ARM execution and an independent clean-machine rebuild have not been demonstrated.

## 2. Restore and inspect the managed environment

Linux/WSL Bash, from the repository root:

```bash
igny init
igny --version
igny workspace sync
igny status
igny env show formal-fifo
igny tool show symbiyosys --env formal-fifo
igny tool show sby --env formal-fifo
igny tool show iverilog --env formal-fifo
igny tool show vvp --env formal-fifo
python3 --version
bash scripts/run.sh identity
cat reports/tool_versions.txt
```

`igny init` initializes the outer workbench shell. `workspace sync` restores the environment from the supplied lock and acquires missing pinned tools. It does not run the proof. `status` should identify this workspace, and `env show` should list both tool bindings. `sby` belongs to `symbiyosys`; `vvp` belongs to `iverilog`. Stop on an acquisition or binding error and inspect the reported diagnostic. A version command alone is not verification of the FIFO.

The supplied workspace marker and lock are already present. Do not create another workspace over them or substitute an unrelated system Yosys/solver. Every runner invocation selects `formal-fifo` explicitly.

## 3. Run every verification stage in order

Linux/WSL Bash:

```bash
bash scripts/run.sh broken
bash scripts/run.sh prove
bash scripts/run.sh cover
bash scripts/run.sh sim
python3 scripts/verify.py
```

The identity command in step 2 is also required before the final observer. The stages have the following dependencies and outputs:

| Command | Work performed | Required outcome / principal artifacts |
|---|---|---|
| `broken` | Prove the preserved broken fixture against the same contract | Expected SBY `FAIL`, exit 2, saved VCD; runner prints `FIFO_BROKEN_ASSERTION_COUNTEREXAMPLE_OBSERVED` |
| `prove` | Prove the corrected FIFO using SMTBMC/Yices | Basecase and induction pass; `build/prove/status`, `reports/prove.log` |
| `cover` | Seek all 12 reachable behaviours | All cover goals reached; `build/cover/PASS` and witness VCD files |
| `sim` | Extract actual witness inputs, cross-check them with saved SMT constraints, simulate both RTL versions, and replay the witness through both | Corrected regression/replay pass; broken regression/replay fail on occupancy; `reports/simulation.log`, `reports/replay_fixed.log`, negative logs |
| `verify.py` | Inspect verdicts, actual copied RTL/properties/task configurations, induction, covers, witness causality, simulations, versions and lock | `FIFO_UNBOUNDED_PROOF_COVERS_CAUSAL_COUNTEREXAMPLE_AND_SIMULATION_VERIFIED`; writes `reports/summary.json` |

`sim` requires the witness from `broken`; `verify.py` requires all preceding stages. The scripts return nonzero when a required condition is missing. Stop and investigate a failed command before proceeding. The intentionally broken design must fail: its outer runner returns success only after checking that failure produced the expected kind of evidence. A compiler error, timeout, missing solver or missing witness does not count as bug detection.

The preserved bug increments occupancy whenever a write is accepted, even if a read is accepted on the same edge. In the witness, occupancy first becomes one, then simultaneous accepted read/write makes the broken count two while the independent queue remains at one. The corrected count update applies +1 for write only, -1 for read only, and zero for both or neither.

## 4. Inspect proof, covers, counterexample and simulation

Linux/WSL Bash:

```bash
cat build/broken/status
cat reports/broken_exit.txt
tail -n 20 reports/broken.log
cat build/prove/status
tail -n 20 reports/prove.log
cat build/cover/PASS
cat reports/counterexample.csv
cat reports/counterexample.json
cat reports/simulation.log
cat reports/replay_fixed.log
cat reports/simulation_broken.log
cat reports/replay_broken.log
cat reports/simulation_broken_exit.txt
cat reports/replay_broken_exit.txt
cat reports/summary.json
```

Require both `returned pass for basecase` and `returned pass for induction`, plus `successful proof by k-induction` in the corrected proof log. `build/cover/PASS` must list all 12 covers: empty, full, rejected read, rejected write, both requests at empty/full, both operations accepted, reset while occupied, nonzero read data, write-pointer wrap, read-pointer wrap and full-to-empty drain.

The corrected regression prints:

```text
FIFO_SIM_PASS cycles=2195 checks=13170 pushes=983 pops=967 simultaneous=394 rejected_writes=95 rejected_reads=168 resets=11
FIFO_REPLAY_PASS cycles=5 checks=30
```

The two corrected markers appear in separate logs. The broken regression fails at testbench cycle 3 and the broken replay at cycle 2, each with `FIFO_SIM_MISMATCH occupancy` and `level=2 expected=1 rst=0 wr=1 rd=1`. Formal and testbench cycle labels use different sampling conventions; they are not interchangeable. Raw VCD state zero is arbitrary pre-reset state and is excluded from the first causal occupancy comparison. The replay uses concrete input cycles only and does not force internal solver state into the DUT.

To regenerate the witness extraction alone after a successful `broken` stage:

```bash
python3 scripts/counterexample.py
```

It writes `reports/counterexample.csv`, `reports/counterexample.json` and `build/replay.mem`. Rerun the complete `sim` stage after any witness change before trusting replay results. The regression includes directed boundary/reset/held-data/wrap tests and a fixed-seed 2,048-cycle randomized sequence. Its six comparisons per cycle check count, flags, valid, ordered/held read data and capacity.

## 5. Troubleshooting

| Symptom | Check and next action |
|---|---|
| Workspace or environment missing | Run from this repository root; inspect `igny status`, then restore the supplied lock with `igny workspace sync` |
| `sby` or `vvp` unbound | Inspect the provider with `igny tool show` above; verify both locked bindings before running |
| Solver/frontend error or timeout | Read the complete mode log and tool identities; this is not an expected FIFO failure |
| Broken stage unexpectedly passes | Check that `formal/fifo_broken.sby` selects `tests/fifo_broken.v`; retain the intended broken fixture |
| No witness/replay input | Run `broken` first; require a real assertion failure and nonempty `build/broken/engine_0/trace.vcd` |
| Corrected proof only reports a bounded check | Use the supplied `prove` task; the observer requires both basecase and temporal induction |
| Observer says source/task changed | Rerun the affected proof and dependent simulation stages against current files; do not reuse stale success logs |
| Random simulation totals differ | Keep the supplied seed/testbench or record a separately reviewed experiment; do not edit expected counts to conceal a failure |
| Logs contain local tool paths | Keep raw logs and proof work directories ignored; only the reviewed compact evidence belongs in Git |

## 6. Open the reviewed whitepaper

Windows PowerShell, from this repository root:

```powershell
Invoke-Item .\docs\Formal_FIFO_Counterexample_and_Proof_Ignytion_A4.pdf
Invoke-Item .\docs\Formal_FIFO_Counterexample_and_Proof_Ignytion_A4.pptx
python scripts\preflight_git.py
```

Use the links at the top if viewing this guide on a Git host. The PDF is searchable; the PPTX is its editable A4 source. The preflight uses Python's standard library and checks their recorded hashes along with the public candidate. It does not rerun formal verification. A Windows host can run preflight against the repository without running the Linux EDA tools.

## 7. Review and prepare Git

Linux/WSL Bash, after reviewing the allowlisted source, tests, compact evidence and documents:

```bash
git status --short
git diff --check
git add -- .
git diff --cached --check
python3 scripts/preflight_git.py
git diff --cached --stat
git diff --cached
git branch --show-current
```

Require `GIT_PREFLIGHT_PASS`. Shell scripts must have Git mode `100755`. If a newly initialized Windows index records this supplied runner as nonexecutable, set its index mode and recheck:

```bash
git update-index --chmod=+x scripts/run.sh
python3 scripts/preflight_git.py
```

Do not force-add ignored proof builds, raw logs, generated simulations, runtime packages, personal configuration or agent/work notes. The new local candidate is staged on `demo/verified`. No project-wide licence grant is invented; the tools retain their authors' licences and credit.

The following commands are **manual commit and publication steps**, not commands already executed by this demonstration. Review the staged content and choose your own author identity and public destination first:

```bash
git config user.name
git config user.email
git commit -m "Add verified formal FIFO demonstration and whitepaper"
git remote -v
PUBLIC_REPOSITORY_URL='REPLACE_WITH_YOUR_PUBLIC_REPOSITORY_URL'
git remote add origin "$PUBLIC_REPOSITORY_URL"
git push -u origin HEAD
```

Replace the placeholder before use. Run `remote add` only if this repository has no `origin`; otherwise inspect `git remote get-url origin` and use the existing approved destination. Reproduction scripts do not commit, change remotes or push.

## Files, sources and limits

`rtl/` contains the corrected FIFO. `tests/fifo_broken.v` preserves the deliberate fault; `tests/tb.v` contains the independent simulation scoreboard. `formal/contract.vh` contains properties and an independent shift-queue model; the three `.sby` files define the broken proof, corrected proof and cover tasks. `scripts/run.sh` orchestrates the managed tools; `counterexample.py` extracts actual solver inputs; `verify.py` binds results to current inputs. `evidence/` retains the reviewed measurement snapshot, while fresh runs write `reports/` locally.

Primary tool references: [YosysHQ SBY quickstart](https://yosyshq.readthedocs.io/projects/sby/en/latest/quickstart.html) and [SBY configuration reference](https://yosyshq.readthedocs.io/projects/sby/en/latest/reference.html). No upstream endorsement is implied.

The results do not cover other widths/depths, asynchronous FIFOs or CDC, fairness or eventual-delivery liveness, clock/reset physical quality, synthesis equivalence, timing closure, FPGA programming/operation, ASIC layout or fabricated silicon. Reset flushes the queue; the contract does not require delivery without accepted reads. This is an untimed RTL safety demonstration.
