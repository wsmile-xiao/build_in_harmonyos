#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for tabbed 0.9 (installed bin/tabbed and bin/xembed).
#
# Really runs the installed programs.  tabbed is an X11 tab container, so its
# full job needs a display server; everything before XOpenDisplay() (tabbed.c
# :1372) is exercisable headless and is what this test asserts:
#   * the version banner, which also proves -DVERSION was not "normalised";
#   * the usage path for an unknown option;
#   * the no-display path, which additionally proves the ELF really loaded its
#     libX11/libXft/libfontconfig runtime closure;
#   * the xembed helper, which upstream links into the *same* X11/Xft/fontconfig
#     closure as tabbed (single .o rule), so it needs that closure too.
#
# Upstream routes EVERY early exit of tabbed through die() -> exit(1), so
# assertions match on stderr TEXT, never on exit codes.  The observed exit
# codes are still printed for the record.
#
# Env: TABBED_BIN, XEMBED_BIN = paths to the installed programs
# Exit: 0 = all checks passed, 1 = at least one failure
#--------------------------------------------------------------------
set -euo pipefail

TABBED="${TABBED_BIN:-tabbed}"
XEMBED="${XEMBED_BIN:-xembed}"

# Work dir goes under ~/tmp, not the home root: TMPDIR on this device *is*
# $HOME, and the workspace contract forbids new loose files there (the recipe's
# E452 runtime dir uses ~/tmp for the same reason).  /tmp itself is read-only.
WORK="$HOME/tmp/tabbed-consumer.$$"
# umask 000 is deliberate and platform-forced, not sloppiness: HMDFS masks it
# to 660 for files and 2771 for directories (measured: drwxrws--x / -rw-rw----),
# so nothing here is world-writable -- 'other' gets no write bit at all.  A
# tighter umask is not an option on this filesystem: with 'umask 077' the
# conan-run context cannot create files inside the directory it just made
# ("can't create .../out.txt: Permission denied", reproduced twice on 2026-09-24
# while this line was being decided).
umask 000
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
OUT="$WORK/out.txt"
RCF="$WORK/rc.txt"
trap 'rm -rf "$WORK"' EXIT

# DISPLAY must be absent, otherwise check 3 could reach a live server.
unset DISPLAY || true

# A hung assertion would hang the whole gate; timeout is used when present.
if command -v timeout >/dev/null 2>&1; then
	WATCHDOG="timeout 30"
else
	WATCHDOG=""
fi

checks=0
fails=0
check() { # check <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

run_and_capture() { # run_and_capture <cmd...>  -> $OUT holds merged output
	set +e
	# shellcheck disable=SC2086
	$WATCHDOG "$@" >"$OUT" 2>&1
	echo $? >"$RCF"
	set -e
}

output_rc() { cat "$RCF"; }

# 1. tabbed -v prints "tabbed-0.9, ..." on stderr and exits 1 by design
#    (man tabbed(1): "-v prints version information to stderr, then exits";
#    the message goes through die(), hence rc=1 - that is not a failure).
run_and_capture "$TABBED" -v
got=$(sed -n '1p' "$OUT")
case "$got" in
	"tabbed-0.9,"*) res=ok ;;
	*)              res=bad ;;
esac
check "tabbed -v reports version 0.9 on stderr (rc=$(output_rc))" "$res" "ok"

# 2. an unknown option prints the usage banner.  -h is NOT a supported option
#    upstream (it only exists as the Ctrl-Shift-h key binding in config.def.h),
#    so it falls through to the same default: usage() path.
run_and_capture "$TABBED" -Z
got=$(sed -n '1p' "$OUT")
case "$got" in
	"usage: "*"tabbed [-dfksv]"*) res=ok ;;
	*)                             res=bad ;;
esac
check "tabbed prints usage on an unknown option (rc=$(output_rc))" "$res" "ok"

# 3. no display server: the program still loads its X11/Xft/fontconfig closure
#    and reaches XOpenDisplay(), which is the strongest headless proof that the
#    dynamic linking really resolved.
run_and_capture "$TABBED"
if grep -q "cannot open display" "$OUT"; then res=ok; else res=bad; fi
check "tabbed reaches XOpenDisplay and reports cannot open display (rc=$(output_rc))" \
	"$res" "ok"

# 4. xembed is a plain stdlib helper: fewer than 3 arguments is a usage error
#    with exit code 2 (xembed.c:17-20) and no X11 code involved.
run_and_capture "$XEMBED" only-one-arg
got=$(sed -n '1p' "$OUT")
rc=$(output_rc)
case "$got" in
	"usage: "*"xembed flag cmd"*) res=ok ;;
	*)                             res=bad ;;
esac
check "xembed prints its usage line with too few arguments (rc=$rc)" "$res" "ok"

echo "TABBED_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
