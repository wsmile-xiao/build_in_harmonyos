#!/usr/bin/env bash
# metar 20190227.1 test_package —— 全离线可判（不访问外网）
#
# metar 的取数 URL 可由环境变量 METARURL 覆盖（src/main.c 的 download_Metar()：
# getenv("METARURL") 为空才用 METARURL 宏里的 NOAA 地址），因此把 NOAA 报文样本
# 写进临时目录、用 file:// 供给 metar，就能在无 NOAA 网络可达性的环境里真实跑完
# 「curl 取数 → parse_NOAA_data() → parse_Metar() → decode_Metar()」全链路。
# curl/8.15.0 的 Protocols 列表含 file（实测 `curl --version` 第 3 行），
# file:// 取数已在本设备跑通（证据：~/tmp/uc2/z75-metar/09-exp6-decode-corrected.log）。
#
# 上游报文头正则（src/metar.c: parse_NOAA_data 的 "^([0-9/]+ [0-9:]+)..."）要求
# 日期用斜杠分隔；连字符日期不匹配，走 "METAR pattern not found in NOAA data."
# 分支（两种写法各实测 3 次，见 ~/tmp/uc2/z75-metar/10-exp7-sample2-and-patch.log）。
# 分隔符在这里用 ASCII 码 47 现拼、不写字面日期，避免任何传输/编辑环节把分隔符
# 改掉后测试静默失真（断言本身也会失败，不会假绿）。
set -u

PASS=0
fail() { echo "FAIL: $*"; exit 1; }
ok() { PASS=$((PASS + 1)); echo "ok  : $*"; }

SL=$(printf '%c' 47)                 # 47 = 斜杠
HDR1="2019${SL}02${SL}27 12:50"      # 16 字节报文头
HDR2="2019${SL}02${SL}27 13:50"

METAR=$(command -v metar || true)
[ -n "$METAR" ] || fail "metar not found in PATH"
echo "metar binary: $METAR"

# ── 临时样本目录：用 mkdir 建目录（HMDFS 上 mktemp -d 建出的 0700 目录对当前进程
# 不可写，即 patches/0001 处理的同一 E011 机制）；全部产物只写临时目录 ──
WORK="${TMPDIR:-$HOME/tmp}/metar-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK/d1" "$WORK/d2" "$WORK/d3" || fail "cannot create $WORK"
trap 'rm -rf "$WORK"' EXIT

_got_bytes() { wc -c < "$1" | tr -d ' '; }

# 样本落盘后回读校验字节数（HMDFS 写入可见性有延迟时最多重试 10 次）
put_sample() {
    _f="$1"; _want="$2"; _body="$3"; _i=0
    printf '%s\n' "$_body" > "$_f"
    while [ "$(_got_bytes "$_f")" != "$_want" ] && [ "$_i" -lt 10 ]; do
        sleep 1; _i=$((_i + 1)); printf '%s\n' "$_body" > "$_f"
    done
    [ "$(_got_bytes "$_f")" = "$_want" ] || fail "sample $_f not readable back (expected $_want bytes)"
}

expect_line() {
    grep -qF "$2" "$WORK/$1" || fail "$1: missing line [$2]"
    ok "$1: [$2]"
}

# ── T1 无参运行：上游 main() 在 argc==1 时打 usage 并 return 1 ──
out=$("$METAR" 2>&1); rc=$?
[ "$rc" -ne 0 ] || fail "T1 no-arg run unexpectedly exited 0"
ok "T1.1 no-arg exit code non-zero (rc=$rc, upstream contract)"
echo "$out" > "$WORK/t1.out"
expect_line t1.out "Usage:"
expect_line t1.out "decode metar"

# ── T2 -h：getopt 'h' 分支 usage + return 0 ──
out=$("$METAR" -h 2>&1); rc=$?
[ "$rc" -eq 0 ] || fail "T2 -h exited rc=$rc, expected 0"
ok "T2.1 -h exit code 0"
echo "$out" > "$WORK/t2.out"
expect_line t2.out "Usage:"

# ── T3 真实解码（站号 EHAM，取数走 file://；样本 = 报文头 16 + 换行 + 报文 44 + 换行 = 62 字节）──
put_sample "$WORK/d1/EHAM.TXT" 62 "$HDR1
EHAM 271250Z 24008KT 9999 FEW020 12/08 Q1010"
out=$(METARURL="file://$WORK/d1" "$METAR" -d EHAM 2>&1); rc=$?
[ "$rc" -eq 0 ] || fail "T3 metar -d EHAM exited rc=$rc"
ok "T3.0 exit code 0"
echo "$out" > "$WORK/t3.out"
expect_line t3.out "EHAM 271250Z 24008KT 9999 FEW020 12/08 Q1010"
expect_line t3.out "Station       : EHAM"
expect_line t3.out "Day           : 27"
expect_line t3.out "Time          : 12:50 UTC"
expect_line t3.out "Wind direction: 240 (WSW)"
expect_line t3.out "Wind speed    : 8 KT"
expect_line t3.out "Visibility    : 9999 M"
expect_line t3.out "Temperature   : 12 C"
expect_line t3.out "Dewpoint      : 8 C"
expect_line t3.out "Pressure      : 1010 hPa"
expect_line t3.out "Clouds        : FEW at 2000 ft"

# ── T4 差分样本（站号以小写入参 → 上游 strupc() 归一大写；字段全部与 T3 不同）──
# 证明确实解码的是「从 URL 取回的那份报文」，不是恒定输出。
put_sample "$WORK/d2/EHGR.TXT" 64 "$HDR2
EHGR 271350Z 05003KT 0600 BKN015 M02/M08 Q1023"
out=$(METARURL="file://$WORK/d2" "$METAR" -d ehgr 2>&1); rc=$?
[ "$rc" -eq 0 ] || fail "T4 metar -d ehgr exited rc=$rc"
ok "T4.0 exit code 0"
echo "$out" > "$WORK/t4.out"
expect_line t4.out "Station       : EHGR"
expect_line t4.out "Wind direction: 50 (NE)"
expect_line t4.out "Visibility    : 600 M"
expect_line t4.out "Temperature   : -2 C"
expect_line t4.out "Dewpoint      : -8 C"
expect_line t4.out "Pressure      : 1023 hPa"
expect_line t4.out "Clouds        : BKN at 1500 ft"
if grep -qF "240 (WSW)" "$WORK/t4.out"; then
    fail "T4.8 EHGR output unexpectedly contains EHAM wind direction"
fi
ok "T4.8 differential: EHAM wind value absent from EHGR output"

# ── T5 反向对照：非法报文头 → 上游走 pattern-not-found，字段不伪造 ──
put_sample "$WORK/d3/EHAM.TXT" 18 "not-a-noaa-header"
out=$(METARURL="file://$WORK/d3" "$METAR" -d EHAM 2>&1); rc=$?
echo "$out" > "$WORK/t5.out"
grep -qF "METAR pattern not found in NOAA data." "$WORK/t5.out" \
    || fail "T5.1 malformed sample did not trigger upstream pattern-not-found path"
ok "T5.1 malformed sample triggers pattern-not-found"
grep -qE "^Station[[:space:]]*:[[:space:]]*$" "$WORK/t5.out" \
    || fail "T5.2 station field not empty on malformed input"
ok "T5.2 station field empty on malformed input (no fabricated data)"

echo "METAR_TEST_ASSERTIONS_PASSED=$PASS"
echo "metar test_package: PASS"
exit 0
