#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build reports
case "${1:-broken}" in
  broken)
    set +e
    igny run --env formal-fifo sby -f -d build/broken formal/fifo_broken.sby >reports/broken.log 2>&1
    code=$?
    set -e
    echo "$code" >reports/broken_exit.txt
    test "$code" -ne 0
    read -r verdict rest <build/broken/status
    test "$verdict" = FAIL
    test -s build/broken/engine_0/trace.vcd
    tail -14 reports/broken.log
    echo FIFO_BROKEN_ASSERTION_COUNTEREXAMPLE_OBSERVED
    ;;
  prove|cover)
    mode="$1"
    igny run --env formal-fifo sby -f -d "build/$mode" "formal/fifo_${mode}.sby" >"reports/${mode}.log" 2>&1
    echo 0 >"reports/${mode}_exit.txt"
    read -r verdict rest <"build/$mode/status"
    test "$verdict" = PASS
    tail -12 "reports/${mode}.log"
    echo "FIFO_${mode^^}_COMPLETED"
    ;;
  sim)
    python3 scripts/counterexample.py
    replay_count=$(wc -l <build/replay.mem)
    for version in fixed broken; do
        source=rtl/fifo.v
        if [ "$version" = broken ]; then source=tests/fifo_broken.v; fi
        igny run --env formal-fifo iverilog -g2012 -s tb -o "build/$version.vvp" tests/tb.v "$source" >"reports/${version}_compile.log" 2>&1
    done
    igny run --env formal-fifo vvp build/fixed.vvp >reports/simulation.log 2>&1
    igny run --env formal-fifo vvp build/fixed.vvp +REPLAY "+REPLAY_COUNT=$replay_count" >reports/replay_fixed.log 2>&1
    set +e
    igny run --env formal-fifo vvp build/broken.vvp >reports/simulation_broken.log 2>&1
    sim_code=$?
    igny run --env formal-fifo vvp build/broken.vvp +REPLAY "+REPLAY_COUNT=$replay_count" >reports/replay_broken.log 2>&1
    replay_code=$?
    set -e
    echo "$sim_code" >reports/simulation_broken_exit.txt
    echo "$replay_code" >reports/replay_broken_exit.txt
    test "$sim_code" -ne 0
    test "$replay_code" -ne 0
    grep -q 'FIFO_SIM_MISMATCH occupancy' reports/simulation_broken.log
    grep -q 'FIFO_SIM_MISMATCH occupancy' reports/replay_broken.log
    cat reports/simulation.log reports/replay_fixed.log
    echo FIFO_BROKEN_SIMULATION_AND_WITNESS_REPLAY_REJECTED
    ;;
  identity)
    igny run --env formal-fifo sby --version >reports/tool_versions.txt 2>&1
    igny run --env formal-fifo iverilog -V >>reports/tool_versions.txt 2>&1
    echo FIFO_MANAGED_TOOL_IDENTITIES_RECORDED
    ;;
  *) exit 2 ;;
esac
