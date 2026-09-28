#!/usr/bin/env bash
# test_ohos_platform.sh — jool-modules-lts 6.18.39 鸿蒙特有测试（rule12）
#
# 断言 OHOS PC 侧的交付契约与平台特有行为（全部读取被测包真实产物，L1e 下
# 破坏包内文件必须失败）：
#   1. bin/ 三件套交付契约（commands.json 声明的 tool 入口）+ ELF 魔数；
#   2. 入口可经 conanrun PATH 发现（commands.json 的 tool 语义）；
#   3. **不得交付预编译内核模块**：整包无 .ko，快照无 .ko/.o/.la 等构建产物；
#   4. 上游源码快照完整（src/mod + test 36 脚本 + dkms.conf + 手册页）；
#   5. OHOS 上 Jool 内核模块永不可加载（无内核构建树/无 root/无 insmod）时，
#      CLI 必须 fail-closed 优雅降级：非零退出 + 可行动提示，不得崩溃。
set -u

PKG="${1:?usage: test_ohos_platform.sh <package_folder>}"
SNAPSHOT="$PKG/share/jool-modules-lts/upstream"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  [ok] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

echo "== OHOS 交付契约 =="

# 1. bin/ 三件套（每项：存在可执行 + ELF 魔数）
for name in jool jool_siit joold; do
    f="$PKG/bin/$name"
    if [ -x "$f" ]; then ok "bin/$name 存在且可执行"; else bad "bin/$name 缺失或不可执行"; continue; fi
    magic=""
    IFS= read -r -n 4 magic < "$f" 2>/dev/null
    if [ "$magic" = "$(printf '\177ELF')" ]; then
        ok "bin/$name 为 ELF 二进制"
    else
        bad "bin/$name 非 ELF（交付占位被破坏？）"
    fi
done

# 2. commands.json 声明的 tool 入口可经 PATH（conanrun）发现
for name in jool jool_siit joold; do
    if command -v "$name" > /dev/null 2>&1; then
        ok "入口 $name 可经 PATH 发现"
    else
        bad "入口 $name 不在 PATH（commands.json tool 语义被破坏）"
    fi
done

# 3. 不得交付预编译内核模块 / 构建产物
KO_COUNT="$(find "$PKG" -name '*.ko' 2>/dev/null | wc -l)"
[ "$KO_COUNT" -eq 0 ] && ok "整包不含预编译 .ko（内核模块不交付）" \
    || bad "发现 $KO_COUNT 个 .ko（违反交付边界）"
O_COUNT="$(find "$SNAPSHOT" \( -name '*.o' -o -name '*.lo' -o -name '*.la' -o -name '*.ko' \) 2>/dev/null | wc -l)"
[ "$O_COUNT" -eq 0 ] && ok "源码快照不含任何构建产物（.o/.lo/.la/.ko）" \
    || bad "快照混入 $O_COUNT 个构建产物文件"

# 4. 上游源码快照完整性
[ -f "$SNAPSHOT/src/mod/nat64/Makefile" ] && ok "快照含内核模块源码 src/mod" \
    || bad "快照缺 src/mod（内核模块源码未交付）"
[ -f "$SNAPSHOT/dkms.conf" ] && ok "快照含 dkms.conf" || bad "快照缺 dkms.conf"
SH_COUNT="$(find "$SNAPSHOT/test" -name '*.sh' 2>/dev/null | wc -l)"
[ "$SH_COUNT" -eq 36 ] && ok "快照含上游全部 36 个测试脚本" \
    || bad "快照 test/ 脚本数 $SH_COUNT（期望 36）"
for m in jool.8 jool_siit.8 joold.8; do
    [ -f "$PKG/share/man/man8/$m" ] && ok "手册页 $m 已交付" || bad "手册页 $m 缺失"
done

# 5. OHOS 平台特有：内核模块缺失时的 fail-closed 降级行为
#    （OHOS 无 Jool 内核模块也无加载途径，这是该平台上的常态路径而非异常路径）
OUT_FILE="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/jool-ohos-test.$$")"
RC=0
"$PKG/bin/jool" instance display >"$OUT_FILE" 2>&1 || RC=$?
OUT="$(cat "$OUT_FILE")"
rm -f "$OUT_FILE"
if [ "$RC" -ne 0 ] && [ "$RC" -ne 139 ] && [ "$RC" -ne 134 ]; then
    ok "OHOS 无内核模块：jool 非崩溃非零退出（rc=$RC）"
else
    bad "OHOS 无内核模块：jool 退出码 $RC（非零且非崩溃才可接受）"
fi
case "$OUT" in
    *"Jool's socket family doesn't seem to exist"*|*"Could not open the socket to kernelspace"*)
        ok "降级提示可行动（指向内核模块缺失原因）" ;;
    *) bad "降级提示缺失，输出: $OUT" ;;
esac

echo "== test_ohos_platform.sh 结果: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
