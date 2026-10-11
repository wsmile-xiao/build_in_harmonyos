#!/usr/bin/env bash
# test_package/test.sh — HarmonyOS consumer test for the packaged rtapd/vsnppd.
#
# Runs on an aarch64 OHOS host with the package's bin/ on PATH (conanrun env).
# rtapd is booted in a self-contained sandbox — every path (sockets, pid file,
# lock dir, device file, route table) lives under one temp dir, so no /var/run
# and no serial hardware is required — and is then driven end-to-end by the
# consumer-side TNPP client built from check_rtapd.c.
#
# usage: test.sh <check_rtapd> <package-bin-dir>
set -eu

CHECK="$1"
BINDIR="$2"
RTAPD="$BINDIR/rtapd"
VSNPPD="$BINDIR/vsnppd"

# rm/rmdir/unlink and some coreutils may be shadowed by exported bash functions
# or by broken GNU builds on the OHOS host; pin the ones used here to /bin.
RM=$(if [ -x /bin/rm ]; then echo /bin/rm; else command -v rm; fi)
GREP=$(if [ -x /bin/grep ]; then echo /bin/grep; else command -v grep; fi)
CAT=$(if [ -x /bin/cat ]; then echo /bin/cat; else command -v cat; fi)

# alive <pid> — true while the process exists and is not a zombie.
# `kill -0` alone is not sufficient: it also succeeds on zombies, and some OHOS
# sandboxes deny signalling a background child (EPERM).  Classify through
# /proc/<pid>/stat first — same approach as the merged
# archives/b/blockdomains/0.1/test_package/test_blockdomains.sh — and fall back
# to `kill -0` when /proc is unavailable.
alive() {
    _p="$1"
    if [ -r "/proc/$_p/stat" ]; then
        _s=$("$CAT" "/proc/$_p/stat" 2>/dev/null || true)
        _s=${_s#*) }
        case "${_s%% *}" in Z*) return 1 ;; esac
        return 0
    fi
    kill -0 "$_p" 2>/dev/null
}

# ---- sandbox directory ----------------------------------------------------
# OHOS restricts AF_UNIX bind(): /tmp is read-only, and user-data dirs — e.g.
# $HOME and the CI worker's TMPDIR ($HOME/.cache/tmp) — are writable but
# reject bind() with EPERM ("Operation not permitted").  A blind `mktemp -d`
# therefore lands in an unusable dir on the CI workers, and rtapd then dies
# with "Error Operation not permitted (1) at bind unix socket".
# Ask the consumer client to probe candidates with a real bind() (same socket
# type/addrlen rtapd uses) and use the first dir that works.
SRCMD=$(if [ -x /bin/mktemp ]; then echo /bin/mktemp; else command -v mktemp; fi)
BASE="$("$CHECK" --pick-sockdir 2>/dev/null || true)"
if [ -z "$BASE" ]; then
    echo "SKIP: 无任何候选目录允许 AF_UNIX bind（平台限制，参照 E046/E051 同类先例）"
    echo "      已探测: \$TMPDIR, \$TMP, \$TEMP, /data/storage/el2/base/temp,"
    echo "              /data/storage/el2/base/cache, /data/storage/el1/base, /dev/shm, /tmp"
    echo "      该平台无法创建 unix socket，无法在沙箱内启动守护进程，测试降级跳过。"
    exit 0
fi
echo "[consumer.ohos.sandbox_dir] AF_UNIX bind 可用目录 = $BASE"
T="$("$SRCMD" -d "$BASE/rtapd-test.XXXXXX")"
PID=""
# shellcheck disable=SC2064
trap 'if [ -n "$PID" ]; then kill -TERM "$PID" 2>/dev/null || true; wait "$PID" 2>/dev/null || true; fi; "$RM" -rf "$T"' EXIT

CONF="$T/rtapd.conf"
DEV="$T/tap_dev.conf"
ROUTE="$T/tap_route.conf"
DUMP="$T/dump"
PAGES="$T/dev01.pgs"
SOCK="$T/queue.out"          # ExtSocketIn (rtnppd -> rtapd)
PIDFILE="$T/rtapd.pid"
LOG="$T/daemon.log"

# ---- sandbox: one file device + one route for the CAP page we will send ----
cat > "$CONF" <<EOF
TNPPAddress	0001
ExtSocketIn	$SOCK
ExtSocketOut	$T/queue.in
PidFile	$PIDFILE
LockDir	$T/lock
DeviceFile	$DEV
RoutingTable	$ROUTE
EOF
printf 'Device\t\t>%s\nDeviceName\tFILE01\n' "$PAGES" > "$DEV"
printf '0001 !1234ABCD TAP:FILE01\n' > "$ROUTE"

# ---- consumer.ohos.rtapd_usage_exit_code ---------------------------------
# Proves the packaged ELF loads and runs on OHOS (dynamic linker, libc startup,
# printf) and that getopt/usage/exit(1) behave.
echo "[consumer.ohos.rtapd_usage_exit_code] rtapd -x 9 -> usage + exit 1"
rc=0
"$RTAPD" -x 9 > "$T/usage.txt" 2>&1 || rc=$?
test "$rc" -eq 1
"$GREP" -q 'rtapd v1.7' "$T/usage.txt"
"$GREP" -q 'Usage: rtapd \[-ds\]' "$T/usage.txt"

# ---- consumer.ohos.rtapd_missing_config_exit2 ----------------------------
echo "[consumer.ohos.rtapd_missing_config_exit2] rtapd -C <missing> -> exit 2"
rc=0
"$RTAPD" -d -s -C "$T/does-not-exist.conf" >/dev/null 2>&1 || rc=$?
test "$rc" -eq 2

# ---- consumer.ohos.vsnppd_usage_exit_code --------------------------------
echo "[consumer.ohos.vsnppd_usage_exit_code] vsnppd -Q -> usage + exit 1"
rc=0
"$VSNPPD" -Q > "$T/vsnppd-usage.txt" 2>&1 || rc=$?
test "$rc" -eq 1
"$GREP" -q 'vsnppd v1.1' "$T/vsnppd-usage.txt"

# ---- boot the daemon inside the sandbox ----------------------------------
echo "[consumer.ohos.daemon_boot_foreground] rtapd -d -s -x 4 -p <dump>"
"$RTAPD" -d -s -x 4 -C "$CONF" -p "$DUMP" > "$LOG" 2>&1 &
PID=$!

# The daemon counts as up once it has bound ExtSocketIn and reached its main
# loop (both observable).  That is a stronger and more portable signal than the
# shell job pid, which some OHOS sandboxes refuse to signal.
i=0
while [ "$i" -lt 60 ]; do
    if [ -S "$SOCK" ] && "$GREP" -q 'Entering into main loop' "$LOG" 2>/dev/null; then
        break
    fi
    alive "$PID" || break
    sleep 0.2; i=$((i + 1))
done
if ! "$GREP" -q 'Entering into main loop' "$LOG" 2>/dev/null; then
    echo "FAIL: rtapd 未进入主循环 (sandbox=$T, socket=$SOCK)"
    sed -n '1,40p' "$LOG"
    exit 1
fi
if ! alive "$PID"; then
    echo "FAIL: rtapd 进入主循环后立即退出 (sandbox=$T)"
    sed -n '1,40p' "$LOG"
    exit 1
fi

# ---- consumer.ohos.daemon_bind_unix_socket -------------------------------
# AF_UNIX SOCK_DGRAM socket()/bind() on OHOS + pid file write.
echo "[consumer.ohos.daemon_bind_unix_socket] ExtSocketIn 已创建为 unix socket"
test -S "$SOCK"
test -s "$PIDFILE"
# The pid file the daemon writes itself must hold a number that names a live
# process.  (It is not compared against the shell job pid: sandboxes that
# wrap the ELF can make the two differ.)
DPID=$("$CAT" "$PIDFILE" 2>/dev/null || true)
case "$DPID" in
    ''|*[!0-9]*) echo "FAIL: pid 文件内容非法: '$DPID'"; exit 1 ;;
esac
alive "$DPID" || { echo "FAIL: pid 文件记录的进程 $DPID 不存活"; exit 1; }

# ---- consumer.ohos.config_parse_dump_override ----------------------------
# The daemon's -p dump is its machine-readable configuration view; it must
# reflect the overridden paths of the sandbox config (parser + file IO).
# 注意：上游 dump_config() 不输出 PidFile 键（其 pid 文件有效性由上一条
# daemon_bind_unix_socket 断言覆盖），这里断言它实际输出的那些覆盖项。
echo "[consumer.ohos.config_parse_dump_override] -p 转储反映沙箱覆盖项"
test -s "$DUMP"
"$GREP" -q "^TNPPAddress 0001$" "$DUMP"
"$GREP" -q "^ExtSocketIn $SOCK$" "$DUMP"
"$GREP" -q "^ExtSocketOut $T/queue.in$" "$DUMP"
"$GREP" -q "^LockDir $T/lock$" "$DUMP"
"$GREP" -q "^DeviceFile $DEV$" "$DUMP"
"$GREP" -q "^RoutingTable $ROUTE$" "$DUMP"
"$GREP" -q "^Device $PAGES$" "$DUMP"

# ---- consumer.ohos.tnpp_cap_page_end_to_end ------------------------------
# Consumer client -> AF_UNIX datagram -> TNPP parse -> CAP page -> route -> file.
echo "[consumer.ohos.tnpp_cap_page_end_to_end] 消费者客户端投递 TNPP CAP 页面"
"$CHECK" "$SOCK" 0001 0042 1234ABCD "HELLO-OHOS-RTAPD" > "$T/client.log" 2>&1
"$GREP" -q 'sent .* TNPP CAP page for pager 1234ABCD' "$T/client.log"

i=0
while [ "$i" -lt 60 ]; do [ -s "$PAGES" ] && break; sleep 0.2; i=$((i + 1)); done
test -s "$PAGES"
"$GREP" -q 'HELLO-OHOS-RTAPD' "$PAGES"
"$GREP" -q "routed to device 'FILE01'" "$LOG"
"$GREP" -q "saved in file '$PAGES'" "$LOG"

# ---- consumer.ohos.cap_page_id_hex_format --------------------------------
# Directly exercises the patched code path: strtoll() + "!%llX", (long long).
# On OHOS musl the unpatched "%qX" makes sprintf fail and the id collapses to "!".
echo "[consumer.ohos.cap_page_id_hex_format] CAP 页面 ID 十六进制格式正确"
"$GREP" -q "CAP page packet to '!1234ABCD' (func 31) from 0042" "$LOG"
if "$GREP" -q "CAP page packet to '!'" "$LOG"; then
    echo "FAIL: pager id was truncated (musl %q 转换符未被替换)"; exit 1
fi

# ---- consumer.ohos.sigterm_graceful_exit ---------------------------------
echo "[consumer.ohos.sigterm_graceful_exit] SIGTERM 被处理并退出"
kill -TERM "$DPID"
i=0
while [ "$i" -lt 60 ]; do alive "$DPID" || break; sleep 0.2; i=$((i + 1)); done
"$GREP" -q 'SIGTERM or SIGINT has received' "$LOG"
"$GREP" -q 'Exiting from main loop' "$LOG"
if alive "$DPID"; then echo "FAIL: rtapd ignored SIGTERM"; exit 1; fi
wait "$PID" 2>/dev/null || true
PID=""

echo "ALL PASS"
