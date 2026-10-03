#!/bin/sh
# L1 test source file - satisfies CI L0c (test source file requirement).
#
# mcabber 1.1.2 ships no upstream test suite, so this is one of the
# supplementary HarmonyOS tests (R51 scenario 3).  The authoritative assertions
# live in conanfile.py test(); this script mirrors them so the checks can also
# be run by hand inside a conanrun environment.
set -eu

OUT="${TMPDIR:-/tmp}/mcabber-version.txt"

# 1. usage banner: the binary is installed and parses argv
mcabber -h

# 2. version + compile-time feature report
mcabber -V | tee "$OUT"

# 3. ncursesw (unicode) and dlopen plug-in support must be compiled in
grep -qi 'unicode support' "$OUT"
grep -qi 'modules support' "$OUT"

# 4. the compiled-in plug-in directory must follow the packaged layout
MODS_DIR=$(sed -n 's/^Modules directory: //p' "$OUT" | head -n 1)
case "$MODS_DIR" in
    */lib/mcabber) ;;
    *) echo "FAIL: unexpected plug-in directory $MODS_DIR" >&2; exit 1 ;;
esac

# 5. an unknown option must exit non-zero
if mcabber --definitely-not-an-option >/dev/null 2>&1; then
    echo "FAIL: mcabber accepted an unknown option" >&2
    exit 1
fi

echo "OK: mcabber supplementary tests passed"
