#!/data/service/hnp/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# test_package/test.sh — ProtoMol 2.0.3 OHOS consumer test
#
# This is the NEW HarmonyOS consumer test case added together with the
# adaptation: it consumes the installed package the way a real user would —
# through the conanrun environment (PATH already contains <package>/bin) — and
# verifies both that the programs start and that a real molecular dynamics
# calculation produces the expected, numerically stable result on the device.
#
# Covered here:
#   1. all six installed programs are on PATH and start
#   2. `protomol --version` reports the packaged version
#   3. upstream example argon_400 (argon.lf.conf) runs a real MD trajectory
#   4. upstream example butane_4 (UA_butane.lf.conf) runs a second, chemically
#      different MD trajectory (bonded + dihedral forces)
#
# Every case asserts: exit status, the reported step count, the presence of the
# energy table, total-energy conservation over the run and the final total
# energy against a recorded reference (tolerance 0.01 kcal/mol).
#
# OHOS note: the installed programs are plain ELF binaries and the OHOS
# /system/bin/sh (mksh) cannot exec them, hence the bash wrapper — see
# test_package/conanfile.py.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

NUMSTEPS=20

BINARIES=(protomol coulomb coords2coords dcd2dcd iSGProtomol xyzviz)

# case_dir|config|energies_file|reference_final_total_energy_kcal_mol
CASES=(
  "argon_400|argon.lf.conf|argon.out.energies.lf|95.9160"
  "butane_4|UA_butane.lf.conf|UA_butane.out.energy|6.8016"
)

HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="$HERE/data"

PASS=0
FAIL=0

ok()  { echo "  [PASS] $*"; PASS=$((PASS + 1)); }
bad() { echo "  [FAIL] $*"; FAIL=$((FAIL + 1)); }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==================================================================="
echo "[test] ProtoMol 2.0.3 — HarmonyOS consumer test"
echo "[test] work dir : $WORK"
echo "[test] data dir : $DATA"
echo "==================================================================="

# ── 1. installed programs are runnable ───────────────────────────────────────
echo "[test] 1/4 installed programs are present and start"
for b in "${BINARIES[@]}"; do
  if ! command -v "$b" >/dev/null 2>&1; then
    bad "program '$b' is not on PATH (conanrun environment broken)"
    continue
  fi
  if "$b" >"$WORK/$b.smoke.log" 2>&1; then
    ok "program '$b' starts and exits 0"
  else
    rc=$?
    bad "program '$b' exited with $rc (log: $WORK/$b.smoke.log)"
  fi
done

# ── 2. version banner ────────────────────────────────────────────────────────
echo "[test] 2/4 protomol reports the packaged version"
# The banner is captured in full BEFORE matching.  Do NOT write
#     if protomol --version 2>&1 | grep -q ...; then
# instead: this script runs with `set -o pipefail`, and `grep -q` exits as soon
# as it matches.  The banner is 1282 bytes spread over 29 lines and therefore
# does not fit in a single stdio flush, so protomol is normally still writing
# when grep leaves - it is then killed by SIGPIPE and the *pipeline* reports
# 141, which makes the `if` false even though the pattern did match.  The race
# is real and intermittent (observed 1 failure in 10 consecutive runs), which is
# exactly how the version assertion used to fail inside `conan create` while the
# binary reported 'ProtoMol Version 2.0.3' correctly.
VERSION_OUT="$(protomol --version 2>&1 || true)"
if [[ "$VERSION_OUT" == *"ProtoMol Version 2.0.3"* ]]; then
  ok "protomol --version reports 'ProtoMol Version 2.0.3'"
else
  bad "protomol --version did not report 2.0.3"
fi

# ── 3./4. real MD runs on upstream examples ──────────────────────────────────
run_case() {
  local case_dir="$1" conf="$2" energies="$3" reference="$4" label="$5"

  echo "[test] $label upstream MD example: $case_dir/$conf ($NUMSTEPS steps)"

  local dir="$WORK/$case_dir"
  local log="$WORK/$case_dir.log"

  if [ ! -d "$DATA/$case_dir" ]; then
    bad "$label initial data missing: $DATA/$case_dir"
    return
  fi
  cp -R "$DATA/$case_dir" "$dir"

  if ! ( cd "$dir" && protomol "$conf" --numsteps "$NUMSTEPS" ) >"$log" 2>&1; then
    bad "$label protomol exited non-zero (log: $log)"
    return
  fi
  ok "$label protomol finished with exit status 0"

  # Every step must have been integrated.
  local last_step
  last_step="$(grep -E '^Step :' "$log" | awk -F, 'END{gsub(/ /,"",$1); sub(/^Step:/,"",$1); print $1}')"
  if [ "$last_step" = "$NUMSTEPS" ]; then
    ok "$label reached step $last_step / $NUMSTEPS"
  else
    bad "$label reached step '${last_step:-<none>}' instead of $NUMSTEPS"
  fi

  # The energy table must exist and carry data rows.
  if [ ! -s "$dir/$energies" ]; then
    bad "$label energy table '$energies' missing or empty"
    return
  fi
  local rows
  rows="$(wc -l < "$dir/$energies")"
  ok "$label energy table '$energies' written ($rows data rows)"

  # Energy must be conserved across the whole trajectory.
  local spread
  spread="$(grep -E '^Step :' "$log" | awk -F'TE :' '{split($2,a," "); print a[1]}' \
            | awk 'NR==1{m=$1} {if($1>m)m=$1; if(NR==1||$1<n)n=$1} END{printf "%.4f", m-n}')"
  if awk -v s="$spread" 'BEGIN{exit !(s < 0.05)}'; then
    ok "$label total energy conserved (max-min = $spread kcal/mol)"
  else
    bad "$label total energy drifted by $spread kcal/mol"
  fi

  # Final total energy must match the recorded OHOS reference.
  local te
  te="$(grep -E '^Step :' "$log" | awk -F'TE :' 'END{split($2,a," "); print a[1]}')"
  if awk -v got="$te" -v ref="$reference" 'BEGIN{d=got-ref; if(d<0)d=-d; exit !(d<=0.01)}'; then
    ok "$label final total energy $te kcal/mol matches reference $reference"
  else
    bad "$label final total energy '$te' differs from reference $reference"
  fi
}

echo "[test] 3/4 upstream example argon_400 (Lennard-Jones, periodic box)"
run_case "argon_400" "argon.lf.conf" "argon.out.energies.lf" "95.9160" "argon_400"

echo "[test] 4/4 upstream example butane_4 (bonded + dihedral + LJ)"
run_case "butane_4" "UA_butane.lf.conf" "UA_butane.out.energy" "6.8016" "butane_4"

# ── summary ─────────────────────────────────────────────────────────────────
echo "==================================================================="
echo "[test] assertions passed: $PASS   failed: $FAIL"
echo "==================================================================="

if [ "$FAIL" -ne 0 ]; then
  echo "[test] RESULT: FAILED"
  exit 1
fi

echo "[test] RESULT: OK — packaged ProtoMol runs real MD calculations on OHOS"
exit 0
