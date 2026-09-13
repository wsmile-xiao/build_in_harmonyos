#!/usr/bin/env bash
# test.sh — msgpack-tools 0.6 功能测试 (消费者功能测试)
# 验证: JSON↔MessagePack 正反转换; 整数/字符串/数组/map/binary; 非法输入。
set -euo pipefail
PASS=0; FAIL=0

if ! WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/mpk.XXXXXX")"; then
    echo "FAIL: cannot create workdir under ${TMPDIR:-/tmp}" >&2
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"error\":\"workdir-create-failed\"}"
    exit 1
fi
trap 'rm -rf "$WORKDIR"' EXIT

# ── 定位被测 CLI (由 conanrun 环境注入 PATH) ──
M2J="$(command -v msgpack2json || true)"
J2M="$(command -v json2msgpack || true)"
if [ -z "$M2J" ] || [ -z "$J2M" ]; then
    echo "FAIL: msgpack2json/json2msgpack not found in PATH" >&2
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"error\":\"binaries-not-found\"}"
    exit 1
fi

ok()  { PASS=$((PASS+1)); echo "  ok: $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL: $1" >&2; }

roundtrip() { # roundtrip <名称> <json内容>
    printf '%s' "$2" > "$WORKDIR/in.json"
    if ! "$J2M" -i "$WORKDIR/in.json" -o "$WORKDIR/out.mp" 2>"$WORKDIR/err"; then
        bad "$1: json2msgpack failed: $(cat "$WORKDIR/err")"; return
    fi
    if ! "$M2J" -i "$WORKDIR/out.mp" -o "$WORKDIR/out.json" 2>"$WORKDIR/err"; then
        bad "$1: msgpack2json failed: $(cat "$WORKDIR/err")"; return
    fi
    got="$(cat "$WORKDIR/out.json")"
    if [ "$got" = "$2" ]; then
        ok "$1 roundtrip"
    else
        bad "$1 roundtrip: expected [$2] got [$got]"
    fi
}

# ── 1. 整数 (含 int64 边界/负数) ──
roundtrip "integer"        '{"int":-42}'
roundtrip "int64 max"      '{"big":9223372036854775807}'
roundtrip "int64 min"      '{"small":-9223372036854775808}'

# ── 2. 字符串/浮点/布尔/null ──
roundtrip "string/float/bool/null" \
    '{"s":"hello msgpack","f":3.5,"t":true,"n":null}'

# ── 3. 数组与 map 嵌套 ──
roundtrip "array/map nested" \
    '{"arr":[1,2,3],"map":{"a":1,"b":[true,null]}}'

# ── 4. binary: 长字符串经 -B 阈值转 bin,-b 回 base64 前缀再往返 ──
printf '%s' '{"s":"bWVzc2FnZXBhY2stdG9vbHMtMC42LWJpbmFyeS10ZXN0LXBheWxvYWQ="}' > "$WORKDIR/bin.json"
"$J2M" -B 22 -i "$WORKDIR/bin.json" -o "$WORKDIR/bin.mp" 2>/dev/null \
    && ok "json2msgpack -B base64->bin convert" \
    || bad "json2msgpack -B base64->bin convert"
if od -An -tx1 "$WORKDIR/bin.mp" | grep -q " c4 "; then
    ok "msgpack bin8 type (0xc4) emitted"
else
    bad "expected msgpack bin8 type in output: $(od -An -tx1 "$WORKDIR/bin.mp" | head -2)"
fi
"$M2J" -b -i "$WORKDIR/bin.mp" -o "$WORKDIR/bin.out.json" 2>/dev/null \
    && ok "msgpack2json -b bin->base64 convert" \
    || bad "msgpack2json -b bin->base64 convert"
if grep -q '"s":"base64:bWVzc2FnZXBhY2stdG9vbHMtMC42LWJpbmFyeS10ZXN0LXBheWxvYWQ="' "$WORKDIR/bin.out.json"; then
    ok "binary roundtrip content preserved"
else
    bad "binary roundtrip: got $(cat "$WORKDIR/bin.out.json")"
fi

# ── 5. CLI 可用性: -h / -v ──
"$M2J" -h >/dev/null 2>&1 && ok "msgpack2json -h" || bad "msgpack2json -h"
"$J2M" -h >/dev/null 2>&1 && ok "json2msgpack -h" || bad "json2msgpack -h"
"$M2J" -v 2>&1 | grep -q "version 0.6" && ok "msgpack2json -v reports 0.6" \
    || bad "msgpack2json -v version"

# ── 6. 非法输入: 损坏 msgpack 与非法 JSON 必须报错退出 ──
printf '\xc7' > "$WORKDIR/bad.msgpack"           # 非法 msgpack 字节
if "$M2J" -i "$WORKDIR/bad.msgpack" -o /dev/null >/dev/null 2>&1; then
    bad "corrupt msgpack input must fail"
else
    ok "corrupt msgpack input rejected"
fi
printf '%s' '{broken json' > "$WORKDIR/bad.json"
if "$J2M" -i "$WORKDIR/bad.json" -o /dev/null >/dev/null 2>&1; then
    bad "invalid JSON input must fail"
else
    ok "invalid JSON input rejected"
fi
printf '\x93\x01\xa1\x62' > "$WORKDIR/trunc.mp"  # 数组头声明3项但只有2项
if "$M2J" -i "$WORKDIR/trunc.mp" -o /dev/null >/dev/null 2>&1; then
    bad "truncated msgpack input must fail"
else
    ok "truncated msgpack input rejected"
fi

echo
echo "functional tests: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"failed\":$FAIL}"
    exit 1
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"total\":$((PASS+FAIL))}"
