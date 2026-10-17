#!/usr/bin/env bash
# Run CLI checks and verify the HarmonyOS mount-table fallback through statfs.
set -euo pipefail

binary=$1
shim=$2
scratch=$3
mkdir -p "$scratch" "$scratch/home"
HOME="$scratch/home"
export HOME
checks=0

fail() {
	printf 'FAIL: %s\n' "$1" >&2
	exit 1
}

if ! version_output=$("$binary" --version 2>&1); then
	fail "wmfsm --version did not exit successfully: $version_output"
fi
if [ "$version_output" != 'wmfsm version: 0.36' ]; then
	fail "unexpected version output: $version_output"
fi
checks=$((checks + 1))

if ! help_output=$("$binary" --help 2>&1); then
	fail "wmfsm --help did not exit successfully: $help_output"
fi
case "$help_output" in
	*'usage: wmfsm '*) ;;
	*) fail "wmfsm --help omitted its usage text" ;;
esac
checks=$((checks + 1))

set +e
LD_PRELOAD="$shim" "$binary" >"$scratch/mount-fallback.log" 2>&1
status=$?
set -e
if [ "$status" -ne 86 ]; then
	cat "$scratch/mount-fallback.log" >&2
	fail "fallback did not parse a mount and complete statfs (exit $status)"
fi
if ! grep -Fq 'WMFSM_PROC_MOUNTS_STATFS_OK' "$scratch/mount-fallback.log"; then
	cat "$scratch/mount-fallback.log" >&2
	fail 'wmfsm did not complete statfs for a mount parsed from /proc/mounts'
fi
if grep -Fq "Can't open /etc/mtab" "$scratch/mount-fallback.log"; then
	cat "$scratch/mount-fallback.log" >&2
	fail 'wmfsm stopped at missing /etc/mtab instead of processing /proc/mounts'
fi
checks=$((checks + 1))

printf '%s\n' "$checks" > "$scratch/checks.count"

printf 'HMBS_WMFSM_CHECKS=%s\n' "$checks"
