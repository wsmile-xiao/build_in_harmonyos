#!/bin/sh
# test_package consumer verification for mmc 1.0 (Mesh-based Monte Carlo).
#
# C1  bare invocation -> upstream banner + usage, exit 0
# C2  real end-to-end simulation on the bundled 40-tetrahedron cube mesh
#     -> exit 0, "total simulated energy" summary, flux file written
#
# Run under OHOS bash (see test_package/conanfile.py).
set -u
cd "$(dirname "$0")" || exit 1

echo "--- mmc 1.0 consumer verification ---"

# C1: banner / usage
out=$("mmc" 2>&1); rc=$?
if [ "$rc" != "0" ]; then echo "FAIL C1: mmc exit=$rc"; exit 1; fi
echo "$out" | grep -q "Mesh-based Monte Carlo" || { echo "FAIL C1: banner not found"; exit 1; }
echo "PASS C1: banner/usage (exit=0)"

# C2: end-to-end photon transport on the bundled mesh
rm -f minicube.dat
out2=$("mmc" -f minicube.inp -s minicube -n 100000 -b 1 -D TP 2>&1); rc2=$?
if [ "$rc2" != "0" ]; then
    echo "FAIL C2: mmc exit=$rc2"; echo "$out2" | tail -5; exit 1
fi
echo "$out2" | grep -q "total simulated energy" || { echo "FAIL C2: no energy summary"; exit 1; }
[ -s minicube.dat ] || { echo "FAIL C2: flux output minicube.dat missing/empty"; exit 1; }
echo "PASS C2: mesh simulation (rc=0, flux output $(wc -l < minicube.dat) lines)"

echo "test mmc/1.0: 2/2 checks PASS"
exit 0
