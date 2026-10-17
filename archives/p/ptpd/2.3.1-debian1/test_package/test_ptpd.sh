#!/bin/sh
# Consumer functional test for the installed ptpd2 (OpenHarmony build).
# Exercises the CLI surface that is meaningful without a PTP-capable NIC:
# version banner, short/long help, default-config dump and per-setting help,
# plus the unknown-option error path. No files are written, so it is safe on
# the read-mostly HomeArea filesystem.
set -eu

BIN="${PTPD_BIN:?PTPD_BIN must point at the installed ptpd2}"
checks=0
fails=0

ck() {
    checks=$((checks + 1))
    if printf '%s\n' "$3" | grep -q -- "$2"; then
        echo "ok  - $1"
    else
        echo "FAIL- $1: expected substring '$2'"
        fails=$((fails + 1))
    fi
}

ck_rc() {
    checks=$((checks + 1))
    if [ "$3" -eq "$2" ]; then
        echo "ok  - $1"
    else
        echo "FAIL- $1: expected exit status $2, got $3"
        fails=$((fails + 1))
    fi
}

out=$("$BIN" -v 2>&1); rc=$?
ck "version banner" "ptpd2 version 2.3.1" "$out"
ck_rc "exit status 0 for -v" 0 "$rc"

out=$("$BIN" -h 2>&1); ck "short help usage" "usage: ptpd2" "$out"
out=$("$BIN" --help 2>&1); ck "long option help" "usage: ptpd2" "$out"

out=$("$BIN" -H 2>&1); ck "long help engine setting" "ptpengine:interface" "$out"
ck "long help exposes all settings" "ptpengine:preset" "$out"

out=$("$BIN" -O 2>&1); ck "default config header" "default configuration" "$out"
ck "default config section" "ptpengine:interface" "$out"

out=$("$BIN" -e ptpengine:interface 2>&1); ck "setting help name" "setting: ptpengine:interface" "$out"
ck "setting help type" "type: STRING" "$out"

out=$("$BIN" -Z 2>&1) || true
ck "unknown option reported" "unrecognized option" "$out"
ck "unknown option guidance" "Run ptpd2 with -h" "$out"

echo "PTPD_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
