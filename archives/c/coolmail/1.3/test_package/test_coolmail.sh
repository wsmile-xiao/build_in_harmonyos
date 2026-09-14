#!/bin/sh
# Functional smoke test for the packaged coolmail executable.
#
# Usage: test_coolmail.sh <package-folder> <coolmail-binary> <workdir> <ld-library-path>
#
# The device and the CI worker are headless: there is no X server binary in
# the image and no OHOS xorg-server/Xvfb is published on the remote, so
# coolmail cannot open its window here.  The checks below still exercise the
# packaged artifact for real:
#
#   1. the packaged binary exists and is executable;
#   2. `coolmail -h` prints the usage screen and exits 0 (the only path that
#      completes without an X display);
#   3. without DISPLAY the program must exit non-zero with Xt's
#      "Can't open display" diagnostic: that loads the dynamic chain
#      (libXt -> libSM/libICE, libX11 -> libxcb/libXau/libXdmcp) and runs the
#      login-name resolution at the top of main() before display init;
#   4. the installed man page and X11 app-defaults resource file exist.
#
# The check count is accumulated at run time and printed in the final line, so
# the reported number can never drift from the number of "OK:" lines emitted.
#
# POSIX sh only (the device shell is toybox ash): no `set -e`/`set -u`, no
# bashisms.  Exit code 126 means the kernel refused to exec the binary and is
# always reported as a failure.

pkg=$1
bin=$2
work=$3
ldpath=$4

checks=0

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

ok() {
    checks=$((checks + 1))
    echo "OK: $1"
}

[ -n "$pkg" ] && [ -n "$bin" ] && [ -n "$work" ] || fail "usage: test_coolmail.sh <pkg> <binary> <workdir> <ldpath>"
[ -d "$work" ] || fail "work directory missing: $work"
[ -f "$bin" ] || fail "packaged coolmail binary missing: $bin"
[ -x "$bin" ] || fail "packaged coolmail binary is not executable: $bin"
ok "packaged binary present and executable"

LD_LIBRARY_PATH="$ldpath${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH

# --- usage screen -------------------------------------------------------------
help_out="$work/coolmail-help.out"
"$bin" -h > "$help_out" 2>&1
rc=$?
if [ "$rc" -eq 126 ]; then
    fail "kernel refused to exec coolmail (rc=126)"
fi
if [ "$rc" -ne 0 ]; then
    fail "coolmail -h exited $rc, expected 0 (output in $help_out)"
fi
ok "coolmail -h exited 0"

if ! grep -q 'Usage:  coolmail \[options\]' "$help_out"; then
    cat "$help_out" >&2
    fail "usage banner missing from 'coolmail -h' output"
fi
ok "usage banner present"

if ! grep -q -- '-f filename' "$help_out"; then
    fail "documented -f option missing from 'coolmail -h' output"
fi
ok "documented options listed"

# --- headless X initialisation path ------------------------------------------
nodisp_out="$work/coolmail-nodisplay.out"
( unset DISPLAY; "$bin" > "$nodisp_out" 2>&1 )
rc=$?
if [ "$rc" -eq 0 ]; then
    fail "coolmail reported success without an X display"
fi
if [ "$rc" -eq 126 ]; then
    fail "kernel refused to exec coolmail (rc=126)"
fi
if ! grep -q "Can't open display" "$nodisp_out"; then
    cat "$nodisp_out" >&2
    fail "Xt display diagnostic missing (exit=$rc)"
fi
ok "headless run exited $rc after loading the X11/Xt chain"

# --- installed resources ------------------------------------------------------
man_page="$pkg/share/man/man1/coolmail.1"
[ -f "$man_page" ] || fail "man page not installed: $man_page"
ok "man page installed"

app_defaults="$pkg/share/X11/app-defaults/Coolmail"
[ -f "$app_defaults" ] || fail "X11 app-defaults resource file not installed: $app_defaults"
ok "X11 app-defaults installed"

echo "coolmail smoke test OK ($checks checks)"
