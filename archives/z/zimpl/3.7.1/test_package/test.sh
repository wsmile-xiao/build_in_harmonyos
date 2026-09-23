#!/data/service/hnp/bin/bash
# test_package/test.sh — functional verification of the zimpl CLI tool.
#
# R34: genuinely executes the installed zimpl binary on a small 0/1 knapsack
# model and asserts the produced .lp file (it is not a print-only stub).
# CI's destructive L1e check re-runs this script with the package's bin/
# moved away and expects a failure, proving the test really depends on the
# zimpl artifact.
#
# Usage: bash test.sh <package_folder>
set -euo pipefail

PKG_ROOT="${1:?usage: test.sh <package_folder>}"
BIN="$PKG_ROOT/bin/zimpl"

# ── 1. binary is installed and executable ────────────────────────────
echo "[test] 1. zimpl binary installed and executable"
[ -x "$BIN" ] || { echo "FAIL: $BIN is missing or not executable"; exit 1; }

# ── 2. translate a small 0/1 knapsack model ─────────────────────────
echo "[test] 2. translate knapsack.zpl with zimpl"
WORK="$(mktemp -d)"
MODEL="$WORK/knapsack.zpl"
cat > "$MODEL" <<'EOF'
# small 0/1 knapsack model
param n := 3;
set ITEMS := { 1..n };
var x[ITEMS] binary;
maximize value: 4*x[1] + 5*x[2] + 6*x[3];
subto capacity: 2*x[1] + 3*x[2] + 4*x[3] <= 5;
EOF
# zimpl writes knapsack.lp next to the model file, so run it in $WORK
(
    cd "$WORK" || exit 1
    "$BIN" -v0 knapsack.zpl
)
LP="$WORK/knapsack.lp"
[ -f "$LP" ] || { echo "FAIL: zimpl did not produce $LP"; exit 1; }

# ── 3. assert the LP contains Maximize and Subject to sections ───────
echo "[test] 3. LP output contains Maximize / Subject to"
grep -q "Maximize" "$LP" || { echo "FAIL: $LP lacks 'Maximize'"; exit 1; }
grep -q "Subject to" "$LP" || { echo "FAIL: $LP lacks 'Subject to'"; exit 1; }

rm -rf "$WORK"
echo "[test] OK: zimpl translated the model to LP"
exit 0
