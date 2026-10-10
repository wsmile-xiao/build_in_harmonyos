#!/usr/bin/env bash
# test.sh — lsix 1.9.1 consumer test for HarmonyOS PC.
#
# lsix renders SIXEL graphics INTO a terminal. CI has no controlling tty and
# no sixel-capable terminal, so tty-dependent behavior is asserted only at
# its verified boundaries (evidence in 1.9.1/notes.md):
#
#   A. Package layout + shebang + dependency presence + bash version gate.
#   B. Argument parsing: upstream has NO --help option; every argument is
#      treated as an image filename. With forced sixel, "--help" is handed
#      to ImageMagick, which reports NoDecodeDelegateForThisImageFormat on
#      stderr. The script never hangs, exits 0 via `trap cleanup EXIT`, and
#      stdout is exactly the 2-byte SIXEL-stop trailer ESC \.
#   C. Missing-ImageMagick boundary: empty PATH -> rc must be exactly 1 and
#      stdout EMPTY. This exit fires at line 67, BEFORE the EXIT trap is
#      registered (line 79), so it survives — unlike case D.
#   D. No-sixel-terminal boundary: no tty response -> stderr carries the
#      "does not report having sixel graphics support" error, but the EXIT
#      trap's `exit 0` OVERWRITES the line-119 `exit 1`. Real contract:
#      rc=0, stdout exactly 2 bytes (ESC \). Asserted as observed.
#   E. Core pipeline with LSIX_FORCE_SIXEL_SUPPORT=1 (no tty needed): pure
#      red PPM -> real SIXEL stream (starts "ESC P 0 ;", ends "ESC \"),
#      palette #0;2;100;0;0 = pure red, proving montage+convert really ran.
#   F. Multi-image montage: red+blue -> palettes #0 red / #1 blue / #2 white
#      (label), raster geometry 756x126 (two-tile layout, pinned IM 7.1.2-23).
#   G. HarmonyOS-specific patch validation: the conanrun PATH has no `stty`
#      (HarmonyOS PC minimal runtime). The 0001 patch must keep the script
#      free of "stty: command not found" noise in every run above.
#
# NOT verifiable without a real terminal (documented, not faked): actual
# sixel rendering, terminal color/geometry autodetection responses, stty
# echo toggling on a real tty.
set -euo pipefail

lsix=${1:?lsix script path required}
bash_bin=${2:?bash path required}
magick=${3:?magick path required}

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
hex() { od -An -tx1 "$1" | tr -d ' \n'; }

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/lsix-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT
cd "$work_dir"

# Deterministic terminal-less environment for every invocation.
export TERM=dumb

# ---------- fixtures: 4x4 solid-color PPMs ----------
make_ppm() { # $1=file, $2=octal-escape format like '\377\0\0'
    printf 'P6\n4 4\n255\n' > "$1"
    i=0
    while [ "$i" -lt 16 ]; do printf "$2" >> "$1"; i=$((i + 1)); done
}
make_ppm red.ppm  '\377\0\0'
make_ppm blue.ppm '\0\0\377'

# ---------- A. package layout, shebang, dependencies ----------
test -f "$lsix"
test ! -d "$lsix"
grep -q '^#!/usr/bin/env bash$' "$lsix"
test -x "$bash_bin"
test -x "$magick"
"$bash_bin" -c 'test ${BASH_VERSINFO[0]} -ge 4'
printf 'PASS A: layout (res/lsix regular file, env-bash shebang, deps present, bash>=4)\n'

# ---------- B. argument parsing: --help is just a filename ----------
set +e
LSIX_FORCE_SIXEL_SUPPORT=1 timeout 60 "$bash_bin" "$lsix" --help >helpf.out 2>helpf.err </dev/null
rc=$?
set -e
[ "$rc" -eq 0 ]
[ "$(wc -c < helpf.out)" -eq 2 ]
[ "$(hex helpf.out)" = 1b5c ]
grep -qF 'NoDecodeDelegateForThisImageFormat `--help' helpf.err
grep -qF 'MissingAnImageFilename' helpf.err
printf 'PASS B: --help passed to ImageMagick as filename; no hang, rc=0, stdout=ESC-backslash only\n'

# ---------- C. missing-ImageMagick boundary (empty PATH) ----------
mkdir -p nopath
set +e
env PATH="$PWD/nopath" "$bash_bin" "$lsix" red.ppm >nomagick.out 2>nomagick.err </dev/null
rc=$?
set -e
[ "$rc" -eq 1 ]
[ "$(wc -c < nomagick.out)" -eq 0 ]
grep -qF 'Please install ImageMagick' nomagick.err
printf 'PASS C: magick missing from PATH: rc=1, empty stdout, upstream error text\n'

# ---------- D. no-sixel-terminal boundary (force flag OFF) ----------
set +e
timeout 60 "$bash_bin" "$lsix" red.ppm >noterm.out 2>noterm.err </dev/null
rc=$?
set -e
[ "$rc" -eq 0 ]
[ "$(wc -c < noterm.out)" -eq 2 ]
[ "$(hex noterm.out)" = 1b5c ]
grep -qF 'does not report having sixel graphics support' noterm.err
printf 'PASS D: no terminal: rc=0 (trap overwrites exit 1), stdout=ESC-backslash, stderr has sixel error\n'

# ---------- E. forced-sixel core pipeline (single image) ----------
set +e
LSIX_FORCE_SIXEL_SUPPORT=1 timeout 90 "$bash_bin" "$lsix" red.ppm >forced.out 2>forced.err </dev/null
rc=$?
set -e
[ "$rc" -eq 0 ]
[ "$(wc -c < forced.out)" -ge 100 ]
[ "$(hex forced.out | head -c 8)" = 1b50303b ]
[ "$(hex forced.out | tail -c 4)" = 1b5c ]
tr -d '\033' < forced.out | grep -qF '#0;2;100;0;0'
printf 'PASS E: forced sixel: real SIXEL stream, palette #0 pure red (montage+convert ran)\n'

# ---------- F. multi-image montage ----------
set +e
LSIX_FORCE_SIXEL_SUPPORT=1 timeout 90 "$bash_bin" "$lsix" red.ppm blue.ppm >two.out 2>two.err </dev/null
rc=$?
set -e
[ "$rc" -eq 0 ]
tr -d '\033' < two.out | grep -qF '#0;2;100;0;0'
tr -d '\033' < two.out | grep -qF '#1;2;0;0;100'
tr -d '\033' < two.out | grep -qF '#2;2;100;100;100'
tr -d '\033' < two.out | grep -qF '"1;1;756;126'
printf 'PASS F: two-image montage: red/blue/white palettes, geometry 756x126\n'

# ---------- G. HarmonyOS patch validation: stty optional ----------
if command -v stty >/dev/null 2>&1; then
    stty_state=present
else
    stty_state=absent
fi
printf 'INFO G: stty is %s on the test PATH (HarmonyOS PC conanrun: absent)\n' "$stty_state"
# The unpatched upstream emits "line 85: stty: command not found" and
# "line 76: stty: command not found" in exactly this environment; the
# packaged (patched) script must not.
for errfile in helpf.err nomagick.err noterm.err forced.err two.err; do
    if grep -qF 'stty: command not found' "$errfile"; then
        fail "patched lsix still emits stty errors in $errfile"
    fi
done
printf 'PASS G: patched script emits no "stty: command not found" in any run above\n'

printf 'ALL TESTS PASSED\n'
