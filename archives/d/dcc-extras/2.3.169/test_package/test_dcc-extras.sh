#!/usr/bin/env bash
# test_dcc-extras.sh — dcc-extras/2.3.169 消费者用例套件（13 例）
#
# 用法: bash test_dcc-extras.sh <package_folder>
#   （conan test_package 以 env="conanrun" 调用，PATH 已注入包内 bin/）
#
# 覆盖：包布局契约 / 上游二进制真实执行 / OHOS 平台专有用例。
# 上游无自动化测试套件（清点证据见 test_package/MANIFEST.yml 与
# reports/test-report.md §1），本套件即本包唯一可执行验证入口。
#
# L1e 破坏性反向验证：用例 1/2/5 直接比对包内文件与其执行结果，
# 移走或替换包内容必然失败。
#
# 注：此处**有意只用 `set -u` 而不加 `set -e`**——本套件需要跑完全部 13 例并汇总
# 计数（每例自判 PASS/FAIL，失败累加而不中断），最后一个用例的退出码即整体结论。
# 加 `set -e` 会在首个失败处提前退出，导致后续用例与计数无法产出。
set -u

PKG="${1:?usage: test_dcc-extras.sh <package_folder>}"
TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT

PASS=0; FAIL=0; SKIP=0
ok()   { PASS=$((PASS+1)); printf '  [PASS] %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  [FAIL] %s -- %s\n' "$1" "${2:-}"; }
skip() { SKIP=$((SKIP+1)); printf '  [SKIP] %s -- %s\n' "$1" "${2:-}"; }

VER="2.3.169"
echo "== dcc-extras/$VER 消费者用例套件 =="
echo "   package_folder = $PKG"

# ── 1. 包布局契约 ───────────────────────────────────────────────────
c1=pkg-layout-bin
miss=""
for b in cdcc dccproc dccif-test; do
    [ -x "$PKG/bin/$b" ] || miss="$miss bin/$b"
done
[ -z "$miss" ] && ok "$c1" || bad "$c1" "缺可执行文件:$miss"

c2=pkg-layout-libexec
miss=""
for b in dccd dccifd dbclean dblist dccsight ck2ip check_ip_range \
         dump-clients dns-helper wlist fix-map start-dccd stop-dccd; do
    [ -x "$PKG/libexec/$b" ] || miss="$miss libexec/$b"
done
[ -z "$miss" ] && ok "$c2" || bad "$c2" "缺可执行文件:$miss"

c3=pkg-layout-cgi-bin-and-config-prototypes
miss=""
for f in cgi-bin/list-msg cgi-bin/chgpasswd cgi-bin/common.pm \
         res/dcc/flod res/dcc/grey_flod res/dcc/whitelist res/dcc/grey_whitelist \
         res/dcc/whiteclnt res/dcc/whitecommon res/dcc/dcc_conf res/dcc/map.txt; do
    [ -f "$PKG/$f" ] || miss="$miss $f"
done
[ -z "$miss" ] && ok "$c3" || bad "$c3" "缺文件:$miss"

c4=pkg-layout-dev-headers-and-libs
miss=""
for f in include/dcc_defs.h include/dcc_config.h include/dcc_clnt.h \
         lib/libdcc.a lib/libclnt.a; do
    [ -f "$PKG/$f" ] || miss="$miss $f"
done
[ -z "$miss" ] && ok "$c4" || bad "$c4" "缺文件:$miss"

# ── 2. 上游二进制真实执行（--version 面） ────────────────────────────
c5=cli-cdcc-version
out="$("$PKG/bin/cdcc" -V 2>&1)" && [ "$out" = "$VER" ] \
    && ok "$c5" || bad "$c5" "cdcc -V 输出=[$out]"

c6=cli-dccproc-version
out="$("$PKG/bin/dccproc" -V 2>&1)" && [ "$out" = "$VER" ] \
    && ok "$c6" || bad "$c6" "dccproc -V 输出=[$out]"

c7=cli-dccif-test-version
out="$("$PKG/bin/dccif-test" -V 2>&1)" && [ "$out" = "$VER" ] \
    && ok "$c7" || bad "$c7" "dccif-test -V 输出=[$out]"

c8=cli-libexec-daemons-version
miss=""
for b in dccd dccifd dblist dccsight check_ip_range dns-helper wlist; do
    out="$("$PKG/libexec/$b" -V 2>&1 | head -1)"
    [ "$out" = "$VER" ] || miss="$miss $b=[$out]"
done
[ -z "$miss" ] && ok "$c8" || bad "$c8" "版本不符:$miss"

# ── 3. 离线功能执行（真实命令，不依赖 DCC 服务器） ───────────────────
c9=cli-cdcc-help-offline-runs
out="$("$PKG/bin/cdcc" -h"$TMPD" help 2>&1)"; rc=$?
if [ $rc -ne 0 ]; then
    bad "$c9" "cdcc help rc=$rc"
elif printf '%s' "$out" | grep -q "version $VER" && \
     printf '%s' "$out" | grep -q "homedir"; then
    ok "$c9"
else
    bad "$c9" "cdcc help 输出未含 'version $VER'/homedir 命令表"
fi

c10=cli-cdcc-homedir-offline-runs
out="$("$PKG/bin/cdcc" -h"$TMPD" homedir 2>&1)"; rc=$?
if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "homedir=$TMPD"; then
    ok "$c10"
else
    bad "$c10" "cdcc homedir rc=$rc out=[$out]"
fi

# ── 4. OHOS 平台专有用例（鸿蒙特有） ─────────────────────────────────
c11=ohos-elf-native-aarch64-musl
if command -v python3 >/dev/null 2>&1; then
    if python3 - "$PKG" <<'PY'
import struct, sys, os
pkg = sys.argv[1]
targets = [os.path.join(pkg, "bin", b)
           for b in ("cdcc", "dccproc", "dccif-test")] + \
          [os.path.join(pkg, "libexec", b)
           for b in ("dccd", "dccifd", "dbclean", "dblist", "dccsight",
                     "ck2ip", "check_ip_range", "dump-clients", "dns-helper",
                     "wlist")]
bad = []
for p in targets:
    d = open(p, "rb").read()
    if d[:4] != b"\x7fELF":
        bad.append(f"{os.path.basename(p)}: not ELF")
        continue
    if d[4] != 2:
        bad.append(f"{os.path.basename(p)}: not ELF64")
        continue
    e_machine = struct.unpack_from("<H", d, 18)[0]
    if e_machine != 0xB7:
        bad.append(f"{os.path.basename(p)}: e_machine=0x{e_machine:x} != AArch64")
        continue
    phoff = struct.unpack_from("<Q", d, 32)[0]
    phentsize = struct.unpack_from("<H", d, 54)[0]
    phnum = struct.unpack_from("<H", d, 56)[0]
    interp = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if struct.unpack_from("<I", d, off)[0] == 3:      # PT_INTERP
            p_off = struct.unpack_from("<Q", d, off + 8)[0]
            p_sz = struct.unpack_from("<Q", d, off + 32)[0]
            interp = d[p_off:p_off + p_sz].decode("utf-8", "replace").strip("\0")
    if interp is None or "musl" not in interp:
        bad.append(f"{os.path.basename(p)}: INTERP={interp!r} 非 musl")
sys.exit(1 if bad else 0)
PY
    then
        ok "$c11"
    else
        bad "$c11" "存在非 OHOS(aarch64/musl) 可执行文件"
    fi
else
    skip "$c11" "无 python3"
fi

c12=ohos-no-shared-lib-shadow
so="$(find "$PKG" -name '*.so' -o -name '*.so.*' | head -5)"
if [ -z "$so" ]; then
    ok "$c12"
else
    bad "$c12" "包内含动态库（R26：存在污染系统同名库风险）: $so"
fi

c13=ohos-patcher-sys-types-compiles
# OHOS 补丁（include/dcc_types.h 补 <sys/types.h>）的编译期验证在
# test_package 的 C 消费者测试（test_dcc.c，CMake 目标 test_dcc）中完成：
# 该程序直接使用 u_char/u_int32_t/caddr_t 并链接 libdcc。
# 此处只复核头文件确实随包交付且含该 include。
if grep -q "#include <sys/types.h>" "$PKG/include/dcc_types.h" 2>/dev/null; then
    ok "$c13"
else
    bad "$c13" "包内 include/dcc_types.h 未含 #include <sys/types.h>（补丁未生效）"
fi

echo "== 结果: 通过=$PASS 失败=$FAIL 跳过=$SKIP =="
[ "$FAIL" -eq 0 ]
