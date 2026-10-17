#!/bin/sh
# Behaviour test for the packaged wmcore executable (Conan test_package).
#
#   usage: test_wmcore.sh <package-folder> <wmcore-binary> <scratch-dir> <ld-path>
#
# wmcore is an X11 dockapp: the drawing loop needs a display, which neither
# this device nor a CI worker provides (no Xorg/Xvfb in the image, no OHOS
# xorg-server in the artifact repo).  What *can* be executed for real here, and
# what this script therefore asserts, is:
#
#   1  the packaged program exists and is executable;
#   2  `wmcore -h` exits 0  (upstream parses -h before touching X, wmcore.c);
#   3  its banner "wmcore 0.0.4" is present - that string comes from
#      PACKAGE_STRING in the config.h that ./config.status generated, so it
#      proves the configure/substitution stage really ran for this build;
#   4  the usage screen lists the documented -d option;
#   5  a headless run stops in the X layer: exit code 1 plus libdockapp's
#      "can't open display" diagnostic, and *no* loader diagnostic - that is
#      the distinction between "the package runs and has no display" and "the
#      package is broken";
#   6  the same run honours DISPLAY (with DISPLAY=:99 the diagnostic names :99);
#   7  negative control (R34): with the Conan runtime library path removed the
#      loader refuses the binary (exit 127, "Error loading shared library"),
#      i.e. the program genuinely resolves libdockapp/libX11/libXext/libXpm
#      from the tested dependency closure instead of any system library;
#   8  the manual page is installed and carries the substituted version, with no
#      unreplaced @PACKAGE_VERSION@ left over;
#   9  the GPL license file is packaged.
#
# The check counter is accumulated at run time and written both to stdout and to
# <scratch>/checks.count, so the number reported to Conan can never drift from
# the number of "OK:" lines actually emitted.
#
# POSIX sh only (the device shell is toybox ash); no bashisms, no set -e.
# Exit code 126/127 from the packaged binary is always a failure here.

pkg=$1
bin=$2
work=$3
ldpath=$4

checks=0

fail() {
    echo "FAIL: $1" >&2
    if [ -n "$2" ] && [ -f "$2" ]; then
        echo "---- captured output: $2 ----" >&2
        sed -n '1,40p' "$2" >&2
        echo "------------------------------" >&2
    fi
    exit 1
}

ok() {
    checks=$((checks + 1))
    echo "OK: $1"
}

[ -n "$pkg" ] && [ -n "$bin" ] && [ -n "$work" ] \
    || fail "usage: test_wmcore.sh <package-folder> <binary> <scratch> <ldpath>" ""
[ -d "$work" ] || fail "scratch directory missing: $work" ""

# --- 1: packaged artifact ----------------------------------------------------
[ -f "$bin" ] || fail "packaged wmcore binary missing: $bin" ""
[ -x "$bin" ] || fail "packaged wmcore binary is not executable: $bin" ""
ok "packaged binary present and executable"

LD_LIBRARY_PATH="$ldpath${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH

# --- 2..4: the -h path, which upstream reaches before opening a display -----
help_out="$work/help.out"
"$bin" -h > "$help_out" 2>&1
rc=$?
[ "$rc" -eq 0 ] || fail "'wmcore -h' exited $rc, expected 0" "$help_out"
ok "wmcore -h exited 0"

grep -q '^wmcore 0\.0\.4 ' "$help_out" \
    || fail "generated PACKAGE_STRING banner missing from 'wmcore -h' output" "$help_out"
ok "version banner 'wmcore 0.0.4' present (config.h substitution works)"

grep -q '^  -d n' "$help_out" \
    || fail "documented -d option missing from the usage screen" "$help_out"
ok "usage screen lists the documented -d option"

# --- 5,6: headless run must stop in the X connection layer -------------------
nodisp_out="$work/no-display.out"
( unset DISPLAY; "$bin" > "$nodisp_out" 2>&1 )
rc=$?
[ "$rc" -ne 126 ] || fail "kernel refused to exec wmcore (rc=126)" "$nodisp_out"
[ "$rc" -ne 127 ] || fail "runtime loader refused wmcore (rc=127)" "$nodisp_out"
[ "$rc" -eq 1 ] || fail "headless wmcore exited $rc, expected 1" "$nodisp_out"
if grep -qi 'Error loading shared library\|No such file or directory\|Error relocating' "$nodisp_out"; then
    fail "headless run failed in the loader, not in the X layer" "$nodisp_out"
fi
grep -q "can't open display" "$nodisp_out" \
    || fail "libdockapp display diagnostic missing (exit=$rc)" "$nodisp_out"
ok "headless run reached the X layer: exit 1 with \"can't open display\""

withdisplay_out="$work/display-99.out"
( DISPLAY=:99 "$bin" > "$withdisplay_out" 2>&1 )
rc=$?
[ "$rc" -eq 1 ] || fail "DISPLAY=:99 run exited $rc, expected 1" "$withdisplay_out"
grep -q 'can.t open display :99' "$withdisplay_out" \
    || fail "wmcore did not report DISPLAY=:99 in its diagnostic" "$withdisplay_out"
ok "DISPLAY=:99 is honoured (diagnostic names :99)"

# --- 7: negative control, the loader really needs the Conan closure ----------
bare_out="$work/no-ldpath.out"
env -u LD_LIBRARY_PATH "$bin" -h > "$bare_out" 2>&1
rc=$?
[ "$rc" -eq 127 ] || fail "loader-refusal control exited $rc, expected 127" "$bare_out"
grep -q 'Error loading shared library' "$bare_out" \
    || fail "loader-refusal control printed no loader diagnostic" "$bare_out"
ok "without the Conan runtime path the loader refuses wmcore (rc=127, R34)"

# --- 8,9: packaged resources -------------------------------------------------
man_page="$pkg/share/man/man1/wmcore.1"
[ -f "$man_page" ] || fail "man page not installed: $man_page" ""
grep -q '"0\.0\.4"' "$man_page" \
    || fail "man page carries no substituted version" "$man_page"
if grep -q '@PACKAGE_VERSION@' "$man_page"; then
    fail "man page still holds an unreplaced @PACKAGE_VERSION@" "$man_page"
fi
ok "man page installed with the substituted version 0.0.4"

license_file="$pkg/licenses/COPYING"
[ -f "$license_file" ] || fail "GPL license file not packaged: $license_file" ""
ok "license file packaged (licenses/COPYING)"

echo "$checks" > "$work/checks.count"
echo "wmcore behaviour test OK ($checks checks)"
