#!/bin/sh
# Consumer assertions for the packaged mlv-smile 1.47.
# Drives the upstream perl launcher (Lanceur/smile) — the real user entry
# point — against the shipped annotated example.
# $1 = res/examples dir from the package, $2 = writable work dir.
set -u
RES="$1"
WORK="$2"
fails=0

rm -rf "$WORK"
mkdir -p "$WORK" || { echo "FAIL: cannot create work dir"; exit 1; }
cd "$WORK" || { echo "FAIL: cannot enter work dir"; exit 1; }
cp "$RES"/param_example "$RES"/fasta "$RES"/alphabet "$RES"/smile . || exit 1

XSMILE="$(command -v x-smile)" || { echo "FAIL: x-smile not in runenv PATH"; exit 1; }
BINDIR="$(dirname "$XSMILE")"
echo "[1] packaged binaries dir: $BINDIR"
ls "$BINDIR" | tr '\n' ' '; echo

# Retarget the launcher's baked relative paths (../P_BLOCS/bin/...) at the
# packaged bin dir, then run it exactly like an upstream user would.
sed -i -e "s|../P_BLOCS/bin/x-smile|$BINDIR/x-smile|" \
       -e "s|../P_BLOCS+DELTA/bin/x-smile_delta|$BINDIR/x-smile_delta|" \
       -e "s|../SigStat/bin/e-smile_shuffling|$BINDIR/e-smile_shuffling|" \
       -e "s|../SigStat/bin/e-smile_against|$BINDIR/e-smile_against|" \
       smile

PERL="$(command -v perl || echo /data/service/hnp/bin/perl)"
out="$(perl smile param_example 2>&1)"; rc=$?
if [ "$rc" -ne 0 ]; then
  echo "FAIL: launcher rc=$rc"
  echo "$out" | tail -5
  fails=$((fails+1))
fi
echo "[2] perl launcher smile param_example (rc=$rc)"

if [ ! -s example ]; then
  echo "FAIL: extraction output 'example' empty"
  fails=$((fails+1))
fi
echo "[3] extraction output 'example' produced and non-empty"

if [ "$fails" -eq 0 ]; then
  echo "consumer assertions: 3/3 PASS"
else
  echo "consumer assertions: FAILED ($fails)"
  exit 1
fi
