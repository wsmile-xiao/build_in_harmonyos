#!/data/service/hnp/bin/bash
# test_package/test_selint.sh — functional test for the selint executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

echo "[test] selint --version"
ver=$(selint --version 2>&1 || true)
echo "$ver"
echo "$ver" | grep -q "1.5.1" || { echo "❌ version mismatch"; exit 1; }
echo "✅ --version OK"

echo "[test] selint --help"
selint --help >/dev/null 2>&1 || { echo "❌ --help failed"; exit 1; }
echo "✅ --help OK"

# Real end-to-end lint: run selint on a minimal .te policy and assert it
# reports a concrete, deterministic finding.  The sample has an av rule whose
# permissions are out of alphabetical order (read before execute), which
# upstream check C-005 ("Permissions in av rule not ordered") always flags.
cat > sample.te <<'TE'
policy_module(sample, 1.0)

type foo_t;
type bar_t;

allow foo_t bar_t : file { read execute };
TE

echo "[test] selint sample.te  (expect C-005 finding)"
out=$(selint sample.te 2>&1 || true)
echo "$out"
# selint must locate the file and emit a C-005 finding on the allow line.
if ! echo "$out" | grep -q "sample.te"; then
  echo "❌ no sample.te diagnostic line"; exit 1
fi
if ! echo "$out" | grep -qE "\(C-005\)"; then
  echo "❌ expected C-005 (unordered permissions) finding in selint output"; exit 1
fi
echo "✅ functional lint OK — C-005 reported on unordered av rule"

echo "[test] selint -F sample.te  (exit code reflects findings)"
# -F makes selint return non-zero when any check fires → proves real analysis.
rc=0
selint -F sample.te >/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 0 ]; then
  echo "❌ -F should exit non-zero when a finding exists (got 0)"; exit 1
fi
echo "✅ -F exit code OK (rc=$rc)"

echo "✅ All functional tests passed"
