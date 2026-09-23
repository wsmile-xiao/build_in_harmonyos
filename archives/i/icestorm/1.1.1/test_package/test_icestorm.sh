#!/bin/sh
set -eu

bin_dir=$1
share_dir=$2

# ---------------------------------------------------------------------------
# 1. Command-line tools (unchanged behaviour from icestorm/1.1)
# ---------------------------------------------------------------------------

pll_output=$("$bin_dir/icepll" -i 12 -o 48)
case "$pll_output" in
  *F_PLLIN*) ;;
  *) exit 1 ;;
esac

for tool in icepack icemulti icebram icetime; do
  status=0
  output=$("$bin_dir/$tool" -h 2>&1) || status=$?
  [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
  case "$output" in
    *Usage:*) ;;
    *) exit 1 ;;
  esac
done

test -x "$bin_dir/iceunpack"

# ---------------------------------------------------------------------------
# 2. iCE40 device databases must be installed
#    Regression: 1.1 packaged none of them (they are build products upstream).
# ---------------------------------------------------------------------------

for device in 384 1k 5k u4k 8k; do
  db="$share_dir/chipdb-$device.txt"
  test -s "$db"
  grep -q "IceBox Chip Database Dump" "$db"
  grep -q "^\.device" "$db"
done

# ---------------------------------------------------------------------------
# 3. Timing tables must still be installed
# ---------------------------------------------------------------------------

for timing in timings_hx1k timings_hx8k timings_lp1k timings_lp384 \
              timings_lp8k timings_u4k timings_up5k; do
  test -s "$share_dir/$timing.txt"
done

# ---------------------------------------------------------------------------
# 4. Runtime resolution: icetime must actually find the database it needs
#    Regression: the recipe compiled CHIPDB_SUBDIR="/share/icebox", which makes
#    the binary search "<prefix>/share//share/icebox/" - a path that never
#    exists.  The device name comes from the .asc, not from -d.
# ---------------------------------------------------------------------------

work="${TMPDIR:-/tmp}"
tmp="$work/icestorm-test-$$"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

printf '.device 1k\n' > "$tmp/min.asc"

lookup=$("$bin_dir/icetime" -v -d hx1k "$tmp/min.asc" 2>&1 || true)
looked_at=$(printf '%s\n' "$lookup" \
  | sed -n 's/^Looking for chipdb .* at \(.*\)$/\1/p' | tail -1)

test -n "$looked_at"
test -f "$looked_at"

echo "icestorm: PLL, 5 CLI entry points, 5 device databases, 7 timing tables, runtime chipdb lookup OK"
