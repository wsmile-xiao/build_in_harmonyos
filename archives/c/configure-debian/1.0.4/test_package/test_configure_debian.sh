#!/bin/bash
# configure-debian 1.0.4 — OHOS 冒烟测试（自写，上游 0 测试用例）
#
# 断言依据（脚本全文核对）：
# - L30 `use strict` 子句 + L32 `use Locale::gettext` —— 编译期硬依赖，
#   Locale/gettext.pm 缺失则 perl -c 都过不了
# - L139 根门禁 EFFECTIVE_USER_ID != 0 → die "must be run as root"，
#   在参数解析之前 —— 非 root CI 下任何参数都命中同一确定性 exit 1 行为
#   （能走到门禁 = 全文件编译 + 模块加载 + 常量表构建均成功）
# - L149/L292 root 交互路径调 dpkg-reconfigure（dpkg 包内 bin/dpkg-reconfigure）
# - shebang OHOS 适配：#!/usr/bin/env perl -w（原 /usr/bin/perl）
#
# 环境适配（实测）：
# - toybox `id -u` 不识别大 uid（'bad uid 20020084' RC=2）——非 root 判定
#   改用 HOME 存在性（root 无 HOME）
# - 本环境 VirtualRunEnv 未把 PERL5LIB 传播到 test 子进程（@INC 实测
#   无该条目）——测试内从包路径自举 export（配方 runenv PERL5LIB 保留
#   给下游消费方）
# - conan runenv 仅含直接依赖的 bindirs——dpkg 是 requires 的依赖包，
#   其 bin 不注入 PATH——从 conan cache 定位包内 dpkg-reconfigure

set -uo pipefail

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "  [PASS] $1"; }
fail() { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }

# 非 root 判定：HOME 存在 = 非 root（root 无 HOME；toybox id -u 对大 uid 报 bad uid）
is_root() { [ -z "${HOME:-}" ]; }

SCRIPT="$(command -v configure-debian 2>/dev/null || true)"
PKG_ROOT=""

# 包根（configure-debian 包）→ vendored perl5lib 路径自举
if [ -n "$SCRIPT" ]; then
    PKG_ROOT="$(cd "$(dirname "$SCRIPT")/.." && pwd)"
    export PERL5LIB="$PKG_ROOT/lib/perl5${PERL5LIB:+:$PERL5LIB}"
fi

echo "=== configure-debian 1.0.4 — OHOS 冒烟测试 ==="
echo

# T00 — 包已装入 env PATH（runenv bindirs）
if [ -z "$SCRIPT" ]; then
    fail "configure-debian 不在 PATH（conan runenv 未注入）"
else
    pass "configure-debian 在 PATH: $SCRIPT"
fi

# T01 — 主脚本存在且可执行
if [ -n "$SCRIPT" ] && [ -x "$SCRIPT" ]; then
    pass "主脚本存在且可执行"
else
    fail "主脚本缺失或不可执行"
fi

if is_root; then
    fail "测试必须在非 root 下运行（CI 沙箱前提）"
    T02_OK=""
else
    T02_OK="1"
fi

# T02 — root 门禁：非 root 实跑必须 exit 1 + stderr 含 "must be run as root"
#      （能过 L32 use Locale::gettext 编译到门禁 = vendored shim 生效）
if [ -n "$T02_OK" ]; then
    OUT="$(perl "$SCRIPT" foo 2>&1)"; RC=$?
    if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q "must be run as root"; then
        pass "非 root 实跑命中 root 门禁（exit 1 + 'must be run as root'——编译期依赖全部可解析）"
    else
        fail "root 门禁断言不符: RC=$RC OUT=$OUT"
    fi
fi

# T03 — --help 分支同样过编译（root 门禁先于参数解析，同一确定性行为）
if [ -n "$T02_OK" ]; then
    OUT="$(perl "$SCRIPT" --help 2>&1)"; RC=$?
    if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q "must be run as root"; then
        pass "--help 分支过编译到 root 门禁（exit 1）"
    else
        fail "--help 分支断言不符: RC=$RC OUT=$OUT"
    fi
fi

# T04 — vendored Locale/gettext.pm 在包内（shim 落位 lib/perl5/Locale/）
P5="$(find "$PKG_ROOT" -name "gettext.pm" -path "*Locale*" 2>/dev/null | head -1 || true)"
if [ -n "$P5" ] && perl -MLocale::gettext -e 'print "shim loads OK\n"' 2>/dev/null | grep -q "shim loads OK"; then
    pass "Locale/gettext.pm 已装入包且可加载（$P5）"
else
    fail "包内未找到 Locale/gettext.pm 或加载失败"
fi

# T05 — 包内 debconf helper 落位（L120/L227 等 system($debconf_helper, ...) 的
#      目标文件 /usr/share/configure-debian/configure-debian-debconf 已归档）
if [ -n "$SCRIPT" ] && [ -x "$PKG_ROOT/share/configure-debian/configure-debian-debconf" ]; then
    pass "debconf helper 在包内（share/configure-debian/configure-debian-debconf 可执行）"
else
    fail "包内未找到可执行的 configure-debian-debconf"
fi

# T06 — shebang 已适配 OHOS（无 /usr/bin/perl，perl 由 hnp 提供）
if [ -n "$SCRIPT" ] && head -1 "$SCRIPT" | grep -q '#!/usr/bin/env perl -w'; then
    pass "shebang 为 #!/usr/bin/env perl -w（OHOS 适配）"
else
    fail "shebang 未适配: $(head -1 "$SCRIPT" 2>/dev/null)"
fi

echo
echo "=== 结果: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
