#!/bin/sh
# cheops smoke test from a consumer point of view.
# Only POSIX sh + the packaged cheops binary + grep are required.
#   - `--version` prints the CHEOPS banner and exits 0
#   - `--help`    prints usage and exits 0
#   - a scripted human/human game drives the real stdin game loop and exits 0
set -e

if [ $# -lt 1 ]; then
    echo "usage: test_cheops.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
P="$BIN/cheops"

[ -x "$P" ] || { echo "cheops binary not found/executable: $P" >&2; exit 1; }

tmp="${TMPDIR:-/tmp}/cheops_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

# --version: banner + exit 0
"$P" --version > "$tmp/ver" 2>&1 || { echo "cheops --version failed" >&2; exit 1; }
grep -q 'CHEOPS' "$tmp/ver" || { echo "no CHEOPS banner; got:" >&2; cat "$tmp/ver" >&2; exit 1; }

# --help: usage + exit 0
"$P" --help > "$tmp/help" 2>&1 || { echo "cheops --help failed" >&2; exit 1; }
grep -qi 'usage: cheops' "$tmp/help" || { echo "no usage line; got:" >&2; cat "$tmp/help" >&2; exit 1; }

# scripted human/human game: choose human for White and Black, play two legal
# opening moves, then quit. Exercises the real game loop (board + move logic).
printf 'h\nh\ne2e4\ne7e5\nquit\n' | "$P" > "$tmp/game" 2>&1 || {
    echo "cheops game run failed" >&2; tail -40 "$tmp/game" >&2; exit 1; }
grep -q 'Command:' "$tmp/game" || { echo "game loop never prompted; got:" >&2; cat "$tmp/game" >&2; exit 1; }

echo "cheops smoke test OK"
