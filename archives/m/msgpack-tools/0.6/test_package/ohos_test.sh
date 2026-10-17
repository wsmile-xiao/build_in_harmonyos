#!/usr/bin/env bash
# ohos_test.sh — msgpack-tools 0.6 鸿蒙(OHOS)特有测试
# 验证: ELF64 AArch64 / NEEDED 白名单 / .codesign 签名 / RPATH 洁净 / 真实转换
#
# NEEDED 判定 (fail-closed):
#   - readelf 执行失败  => 直接 FAIL (绝不误判为全静态)
#   - 无 NEEDED 条目    => 接受为全静态 (musl 静态链接)
#   - 有 NEEDED 条目    => 逐条解析 [库名], 必须全部命中白名单, 任何一条
#                          未命中即整体 FAIL (不做 "包含一个合法库就放行" 的宽松匹配)
#   - 白名单 (与 RPATH/脏依赖检查共用同一语义):
#       libc.so  libc.so.*  libc++_shared.so  libc++_shared.so.*
#     其余一律拒绝: libstdc++* / glibc loader (ld-linux*) / libm / 未列入者
set -euo pipefail
PASS=0; FAIL=0

if ! WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/mpk-ohos.XXXXXX")"; then
    echo "FAIL: cannot create workdir under ${TMPDIR:-/tmp}" >&2
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"error\":\"workdir-create-failed\"}"
    exit 1
fi
trap 'rm -rf "$WORKDIR"' EXIT

M2J="$(command -v msgpack2json || true)"
J2M="$(command -v json2msgpack || true)"
if [ -z "$M2J" ] || [ -z "$J2M" ]; then
    echo "FAIL: msgpack2json/json2msgpack not found in PATH" >&2
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"error\":\"binaries-not-found\"}"
    exit 1
fi

ok()  { PASS=$((PASS+1)); echo "  ok: $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL: $1" >&2; }

# OpenHarmony NEEDED 白名单: 逐条精确匹配, 与 RPATH 脏依赖检查共用此语义
ohos_lib_allowed() {
    case "$1" in
        libc.so|libc.so.*|libc++_shared.so|libc++_shared.so.*) return 0 ;;
        *) return 1 ;;
    esac
}

# ── 1. ELF64 AArch64 ──
for tool in "$M2J" "$J2M"; do
    name="$(basename "$tool")"
    hdr="$(head -c 20 "$tool" 2>/dev/null | od -An -v -tx1 | tr -d ' \n' || true)"
    # e_ident: magic(4) + class(1)=2 + data(1)=1 + version(1)=1
    if [ "${hdr:0:8}" = "7f454c46" ] && [ "${hdr:8:2}" = "02" ] && [ "${hdr:10:2}" = "01" ] && [ "${hdr:12:2}" = "01" ]; then
        ok "$name: ELF64 little-endian (EI_CLASS=2, EI_DATA=1)"
    else
        bad "$name: not ELF64 LSB (header=$hdr)"
    fi
    # e_machine (offset 18, 2 bytes LE) == 0x00b7 → AArch64
    if [ "${hdr:36:4}" = "b700" ]; then
        ok "$name: e_machine AArch64 (0xB7)"
    else
        bad "$name: e_machine != AArch64 (got ${hdr:36:4})"
    fi
    # e_type (offset 16) == 0x0002 ET_EXEC / 0x0003 ET_DYN
    case "${hdr:32:4}" in
        0200) ok "$name: e_type ET_EXEC" ;;
        0300) ok "$name: e_type ET_DYN" ;;
        *) bad "$name: unexpected e_type ${hdr:32:4}" ;;
    esac
done

# ── 2. NEEDED 白名单: readelf 失败必须 FAIL; 无 NEEDED=全静态; 有则逐条校验 ──
for tool in "$M2J" "$J2M"; do
    name="$(basename "$tool")"
    if dyn="$(readelf -d "$tool" 2>/dev/null)"; then
        # 逐条提取 NEEDED 行方括号内库名; sed 无匹配输出为空 => 全静态
        needed="$(printf '%s\n' "$dyn" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p')"
        if [ -z "$needed" ]; then
            ok "$name: fully static (musl static-linked, no NEEDED)"
            continue
        fi
        bad_libs=""
        while IFS= read -r lib; do
            [ -n "$lib" ] || continue
            if ! ohos_lib_allowed "$lib"; then
                bad_libs="${bad_libs}'${lib}' "
            fi
        done <<< "$needed"
        if [ -z "$bad_libs" ]; then
            libs_one_line="$(printf '%s\n' "$needed" | tr '\n' ' ')"
            ok "$name: all NEEDED whitelisted for OHOS ($libs_one_line)"
        else
            bad "$name: NEEDED outside OHOS whitelist: $bad_libs(allowed: libc.so, libc.so.*, libc++_shared.so, libc++_shared.so.*; libstdc++/glibc loader rejected)"
        fi
    else
        bad "$name: readelf -d failed (rc=$?) — fail closed, NOT treated as static"
    fi
done

# ── 3. .codesign 签名段存在且唯一 (OHOS ELF 自签名) ──
for tool in "$M2J" "$J2M"; do
    name="$(basename "$tool")"
    if sw="$(readelf -SW "$tool" 2>/dev/null)"; then
        n="$(printf '%s\n' "$sw" | grep -c '\.codesign' || true)"
        if [ "$n" = "1" ]; then
            ok "$name: .codesign section present"
        else
            bad "$name: .codesign section count=$n (expected 1)"
        fi
    else
        bad "$name: readelf -SW failed (rc=$?) — fail closed"
    fi
done

# ── 4. RPATH/RUNPATH 洁净: 无构建机绝对路径 / glibc loader / libstdc++ ──
# (NEEDED 合法性由第 2 节白名单统一约束, 两处共用同一白名单语义)
for tool in "$M2J" "$J2M"; do
    name="$(basename "$tool")"
    if dyn="$(readelf -d "$tool" 2>/dev/null)"; then
        dirty="$(printf '%s\n' "$dyn" | grep -E 'RPATH|RUNPATH' | grep -E '/storage/|/data/service|/home/|ld-linux|libstdc\+\+' || true)"
        if [ -z "$dirty" ]; then
            ok "$name: RPATH/RUNPATH clean (no buildhost paths, no host loaders)"
        else
            bad "$name: dirty RPATH/RUNPATH entries:"
            printf '%s\n' "$dirty" >&2
        fi
    else
        bad "$name: readelf -d failed (rc=$?) — fail closed"
    fi
done

# ── 5. 真实转换在 OHOS 上运行成功 ──
printf '%s' '{"ohos":"鸿蒙PC","tools":["msgpack2json","json2msgpack"],"n":1}' > "$WORKDIR/oh.json"
if "$J2M" -i "$WORKDIR/oh.json" -o "$WORKDIR/oh.mp" >/dev/null 2>&1 \
   && "$M2J" -i "$WORKDIR/oh.mp" -o "$WORKDIR/oh.out.json" >/dev/null 2>&1 \
   && grep -q "鸿蒙PC" "$WORKDIR/oh.out.json"; then
    ok "real conversion on OHOS (JSON→MP→JSON, UTF-8 string preserved)"
else
    bad "real conversion on OHOS failed"
fi

echo
echo "ohos-specific tests: PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"failed\":$FAIL}"
    exit 1
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"total\":$((PASS+FAIL))}"
