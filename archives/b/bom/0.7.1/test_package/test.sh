#!/data/service/hnp/bin/bash
# Consumer smoke test for bom on HarmonyOS.
# Runs with conanrun env: the packaged bin/ is on PATH.
set -eu

echo "[test] bom resolved to: $(command -v bom)"

echo "[test] 1) bom version (loose assertion: tarball build has no git tag)"
bom version

echo "[test] 2) bom generate produces a valid SPDX 2.3 document from a fixture"
workdir="bom_tp_out_$$"
mkdir -p "$workdir"
printf 'module example.com/bom-test-fixture\n\ngo 1.24\n' > "$workdir/fixture.txt"
bom generate -n bom-smoke-test -f "$workdir/fixture.txt" -o "$workdir/fixture.spdx"
grep -q "SPDXVersion: SPDX-2.3" "$workdir/fixture.spdx"
grep -q "Creator: Tool: bom-" "$workdir/fixture.spdx"
rm -rf "$workdir"

echo "[test] PASS: bom works on HarmonyOS"
