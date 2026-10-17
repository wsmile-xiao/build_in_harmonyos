#!/bin/bash
# test_package consumer smoke test for pla 1.3.
# Runs the real `pla` binary and asks it to render a Gantt chart PNG via cairo.
#
# HarmonyOS HMDFS quirk (knowledge E073): the dynamic loader cannot follow .so
# symlinks, so the shared libraries pla needs are copied into a staging dir as
# real files before pla is executed.  Only the exact SONAMEs pla requires are
# staged, and they are picked from the FIRST directory that provides them
# (conanrun places the conan dependency dirs before any inherited paths), so a
# stale host copy (e.g. /usr/local/lib) can never shadow the conan one.
set -eu

HOME_TMP="${TMPDIR:-$HOME/tmp}"
mkdir -p "$HOME_TMP"
STAGE="$HOME_TMP/pla-runtime-$$"
mkdir -p "$STAGE"

# SONAMEs pla needs at runtime (from: llvm-readelf -d pla | grep NEEDED)
NEEDED="libcairo.so.2 libpixman-1.so.0 libpng16.so.16 libfontconfig.so.1 libexpat.so.1 libfreetype.so.6"

for dir in $(printf '%s' "$LD_LIBRARY_PATH" | tr ':' ' '); do
    [ -n "$dir" ] || continue
    [ -d "$dir" ] || continue
    for so in $NEEDED; do
        [ -e "$STAGE/$so" ] && continue   # already staged from an earlier dir
        if [ -e "$dir/$so" ]; then
            if [ -L "$dir/$so" ]; then
                # copy the real file behind the symlink (E073)
                src="$dir/$(readlink "$dir/$so")"
            else
                src="$dir/$so"
            fi
            [ -f "$src" ] && cp -f "$src" "$STAGE/$so" || true
        fi
    done
done

# all required SONAMEs must now be real files in the staging dir
for so in $NEEDED; do
    if [ ! -f "$STAGE/$so" ]; then
        echo "FAIL: could not stage $so from LD_LIBRARY_PATH" >&2
        exit 1
    fi
done
export LD_LIBRARY_PATH="$STAGE"

# pla must be on PATH (conanrun adds its bin/ dir)
PLA="$(command -v pla)"
test -n "$PLA"
echo "pla binary: $PLA"

echo "=== Test 1: pla CLI smoke ==="
"$PLA" --version >/dev/null 2>&1 || true
"$PLA" -h >/dev/null 2>&1
echo "PASS: pla accepts -h"

echo "=== Test 2: pla renders a real Gantt chart PNG ==="
INPUT="$HOME_TMP/pla-sample-$$.pla"
OUT="$HOME_TMP/pla-sample-$$.png"
cat > "$INPUT" <<'EOF'
[spec] Requirements gathering
	start 2024-03-01 08
	duration 8
[impl] Implementation
	start 2024-03-02 08
	duration 16
	dep spec
	percent 25
[test] Validation
	start 2024-03-05 08
	duration 8
	dep impl
EOF

"$PLA" -i "$INPUT" -o "$OUT" -f png -l en

test -s "$OUT"
# PNG magic: 89 50 4E 47
MAGIC="$(head -c 4 "$OUT" | od -An -tx1 | tr -d ' \n')"
test "$MAGIC" = "89504e47"
echo "PASS: pla produced a real PNG ($(wc -c < "$OUT") bytes)"

echo "=== All pla test_package checks passed ==="
rm -f "$INPUT" "$OUT"
