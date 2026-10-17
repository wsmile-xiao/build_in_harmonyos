#!/data/service/hnp/bin/bash
set -euo pipefail

test_dir="$(cd "$(dirname "$0")" && pwd)"
rm -f bochs.log bochs.stdout

echo "[step] Checking the Bochs command-line interface"
set +e
bochs_help="$(bochs -h 2>&1)"
bochs_help_status=$?
bximage_help="$(bximage --help 2>&1)"
bximage_help_status=$?
set -e

printf '%s\n' "$bochs_help"
echo "        [info] bochs -h exited with status $bochs_help_status"
if (( bochs_help_status >= 126 )); then
  echo "        [fail] bochs could not be executed"
  exit 1
fi
if ! grep -q "Bochs" <<<"$bochs_help"; then
  echo "        [fail] bochs -h output did not identify Bochs"
  exit 1
fi
echo "        [ok] bochs command is available"

printf '%s\n' "$bximage_help"
echo "        [info] bximage --help exited with status $bximage_help_status"
if (( bximage_help_status >= 126 )); then
  echo "        [fail] bximage could not be executed"
  exit 1
fi
if ! grep -qi "bximage" <<<"$bximage_help"; then
  echo "        [fail] bximage --help output did not identify bximage"
  exit 1
fi
echo "        [ok] bximage command is available"

set +e
bochs -qf "$test_dir/bochsrc.txt" -rc "$test_dir/debugger.txt" \
  >bochs.stdout 2>&1 &
bochs_pid=$!
# Bound the test if a regression prevents the BIOS panic from terminating Bochs.
( sleep 30; kill "$bochs_pid" 2>/dev/null || true ) &
watchdog_pid=$!
wait "$bochs_pid"
bochs_status=$?
# The watchdog may already have exited after Bochs terminated normally.
kill "$watchdog_pid" 2>/dev/null || true
wait "$watchdog_pid" 2>/dev/null || true
set -e

test "$bochs_status" -ne 0
grep -Fq "No bootable device." bochs.log

echo "        [ok] Bochs headless BIOS smoke test passed"
