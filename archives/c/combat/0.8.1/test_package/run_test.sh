#!/bin/sh
# run_test.sh — Combat test_package 入口（真实 IIOP 回环，验证打包产物）
# usage: run_test.sh <orb_dir> <tclkill_dir> <test_script_dir>
set -e

ORB_DIR="$1"
KILL_DIR="$2"
SCRIPT_DIR="$3"

command -v tclsh8.6 >/dev/null 2>&1 || {
    echo "FAIL: tclsh8.6 not found on PATH (tcl dependency runenv missing?)"
    exit 1
}

cd "$SCRIPT_DIR"
exec tclsh8.6 ./test_combat.tcl "$ORB_DIR" "$KILL_DIR"
