#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for mergerfs 2.40.2 (installed CLI + preload library).
#
# Env:
#   MERGERFS_BIN      path to the installed mergerfs executable
#   MERGERFS_PRELOAD  path to the installed preload.so
#   MERGERFS_MAN      path to the installed mergerfs.1 man page
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

BIN="${MERGERFS_BIN:?MERGERFS_BIN must point to the installed mergerfs executable}"
PRELOAD="${MERGERFS_PRELOAD:?MERGERFS_PRELOAD must point to the installed preload.so}"
MAN="${MERGERFS_MAN:?MERGERFS_MAN must point to the installed mergerfs.1}"

WORK="${TMPDIR:-.}/mergerfs-test.$$"
mkdir -p "$WORK" || { echo "FAIL: cannot create workdir $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

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

contains() { # contains <file> <pattern>
	if grep -q -F -- "$2" "$1"; then echo 0; else echo 1; fi
}

nonzero() { # nonzero <rc> -> 0 when the command failed
	if [ "$1" != "0" ]; then echo 0; else echo 1; fi
}

# 1. installed binary is a real executable
if [ -x "$BIN" ]; then rc=0; else rc=1; fi
check "mergerfs binary is executable" "$rc" 0

# 2. preload library installed
if [ -f "$PRELOAD" ]; then rc=0; else rc=1; fi
check "preload.so installed" "$rc" 0

# 3. man page installed
if [ -f "$MAN" ]; then rc=0; else rc=1; fi
check "mergerfs.1 man page installed" "$rc" 0

# 4. --version exits 0
"$BIN" --version > "$WORK/ver.txt" 2>&1 && rc=0 || rc=$?
check "mergerfs --version exit status" "$rc" 0

# 5. --version reports the built version
check "mergerfs --version reports 2.40.2" \
	"$(contains "$WORK/ver.txt" 'mergerfs v2.40.2')" 0

# 6. --version carries the upstream license banner
check "mergerfs --version prints ISC license" \
	"$(contains "$WORK/ver.txt" 'ISC License')" 0

# 7. -h exits 0
"$BIN" -h > "$WORK/help.out" 2>&1 && rc=0 || rc=$?
check "mergerfs -h exit status" "$rc" 0

# 8. -h prints the usage banner
check "mergerfs -h prints usage" \
	"$(contains "$WORK/help.out" 'Usage: mergerfs')" 0

# 9. running with no arguments fails (misuse is rejected, not silently accepted)
"$BIN" > "$WORK/noargs.out" 2>&1 && rc=0 || rc=$?
check "mergerfs with no arguments returns non-zero" "$(nonzero "$rc")" 0

# 10. a real mount attempt reaches the FUSE layer but cannot mount in the OHOS
#     sandbox (no accessible /dev/fuse): it must fail instead of hanging.
mkdir -p "$WORK/branch" "$WORK/mnt"
if command -v timeout >/dev/null 2>&1; then
	timeout 20 "$BIN" "$WORK/branch" "$WORK/mnt" -f > "$WORK/mount.out" 2>&1 && rc=0 || rc=$?
else
	"$BIN" "$WORK/branch" "$WORK/mnt" -f > "$WORK/mount.out" 2>&1 && rc=0 || rc=$?
fi
check "mergerfs mount attempt fails without /dev/fuse" "$(nonzero "$rc")" 0

echo "MERGERFS_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
