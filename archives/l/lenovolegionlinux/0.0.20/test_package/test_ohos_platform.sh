#!/usr/bin/env bash
# 鸿蒙特有测试 — OHOS PC 平台行为、打包契约与内核态交付边界
#
# 为什么这些断言是「鸿蒙特有」：
#   * OHOS PC 上没有 Legion 的 ACPI/WMI 固件接口（PNP0C09），内核模块既无法在本仓
#     适配框架内构建，也无法加载 → 交付的 CLI 在该平台上的**真实行为**是「优雅降级」，
#     这正是本脚本锁定、且与 Linux 桌面发行版不同的平台契约；
#   * OHOS 侧 python 布局（site-packages）、控制台入口、不得交付预编译 .ko、
#     以及 argcomplete 可选化，都是适配后的平台特有约束。
#
# 用法：test_ohos_platform.sh <package_folder> [python3 路径]
set -euo pipefail

PKG="${1:-}"
PY="${2:-python3}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "[ohos][FAIL] usage: test_ohos_platform.sh <package_folder> [python3]" >&2
    exit 2
fi

fail() { echo "[ohos][FAIL] $*" >&2; exit 1; }
pass() { echo "[ohos][ ok ] $*"; }

# ── 1. 打包契约：OHOS 侧 site-packages 布局 + 控制台入口 ──
# find 无结果时返回 1：结果为空由下一条断言处理，故此处忽略其退出码
SITE="$(find "$PKG/lib" -maxdepth 3 -type d -name site-packages -print -quit 2>/dev/null || true)"
[ -n "$SITE" ] || fail "site-packages layout missing under $PKG/lib"
[ -f "$SITE/legion_linux/legion_cli.py" ] || fail "legion_cli.py missing in $SITE"
[ -f "$SITE/legion_linux/legion.py" ] || fail "legion.py missing in $SITE"
[ -x "$PKG/bin/legion_cli" ] || fail "bin/legion_cli missing or not executable"
pass "site-packages layout + bin/legion_cli entry point"

# ── 2. 目标解释器可导入交付模块（OHOS 侧 Python） ──
"$PY" - "$SITE" <<'PYEOF'
import sys

sys.path.insert(0, sys.argv[1])
from legion_linux import legion  # noqa: E402

assert legion.LEGION_SYS_BASEPATH.startswith("/sys/module/legion_laptop/"), \
    legion.LEGION_SYS_BASEPATH
print("[ohos][ ok ] packaged legion_linux imports under Python", sys.version.split()[0])
PYEOF

# ── 3. OHOS 平台特有行为：无 Legion 内核接口时 CLI 必须优雅降级 ──
if [ -e /sys/module/legion_laptop ]; then
    echo "[ohos][info] host exposes /sys/module/legion_laptop (not the OHOS PC baseline);"
    echo "[ohos][info] graceful-degradation assertions are therefore reported, not asserted"
    # 退出码不作为断言（上游 main() 不传播子命令返回值），失败仅用于信息展示
    legion_cli --donotexpecthwmon minifancurve-status >/dev/null 2>&1 || true
    pass "CLI executed on a host that has the kernel interface"
else
    # 退出码不作为断言（上游 main() 不传播子命令返回值，降级信息走 stdout）：
    # 断言对象是「降级提示 + 无 traceback」这两条平台行为契约
    OUT="$(legion_cli --donotexpecthwmon minifancurve-status 2>&1 || true)"
    case "$OUT" in
        *"Command not available because feature is not available or kernel module is not loaded."*)
            pass "CLI reports the missing kernel interface instead of fabricating features"
            ;;
        *)
            fail "unexpected CLI output without the Legion kernel module: $OUT"
            ;;
    esac
    case "$OUT" in
        *Traceback*) fail "CLI crashed instead of degrading gracefully: $OUT" ;;
        *) pass "no Python traceback (graceful degradation) on the OHOS PC baseline" ;;
    esac
fi

# ── 4. 适配契约：CLI 不得硬依赖 argcomplete（补丁 0001 必须生效） ──
if grep -qE '^import argcomplete$' "$SITE/legion_linux/legion_cli.py"; then
    fail "legion_cli.py still hard-requires argcomplete (patch 0001 not effective)"
fi
pass "argcomplete optional (patch 0001 effective)"

# ── 4b. 适配契约：legion.py 不得硬编码 bash（补丁 0002 必须生效） ──
# OHOS PC 只提供 POSIX shell；bash 缺失时上游的 Popen(['bash', ...]) 会以
# FileNotFoundError 终止 LegionModelFacade 构造，使 CLI 直接崩溃（补丁 0002 修此）。
if grep -qE "Popen\(\['bash'" "$SITE/legion_linux/legion.py"; then
    fail "legion.py still hard-requires bash (patch 0002 not effective)"
fi
grep -qE "^SHELL = shutil.which\('bash'\)" "$SITE/legion_linux/legion.py" \
    || fail "legion.py has no portable SHELL selection (patch 0002 not effective)"
pass "shell selection portable, no hard bash dependency (patch 0002 effective)"

# ── 5. 完整性：不得交付预编译内核模块（R19 / 不伪造产物） ──
# find 无结果时返回 1：空结果即通过，故此处忽略其退出码
KO="$(find "$PKG" -name '*.ko' -print -quit 2>/dev/null || true)"
[ -z "$KO" ] || fail "prebuilt kernel module shipped in package: $KO"
pass "no prebuilt .ko shipped (kernel-state build is not claimed)"

# ── 6. 上游源码快照随包交付（平台将来提供内核构建树时可直接复用） ──
[ -f "$PKG/share/lenovolegionlinux/upstream/kernel_module/legion-laptop.c" ] \
    || fail "upstream kernel module source snapshot missing"
[ -x "$PKG/share/lenovolegionlinux/upstream/tests/test_python_cli.sh" ] \
    || fail "upstream test scripts in the snapshot are not executable"
pass "upstream source snapshot shipped (kernel_module/ + tests/ + python/)"

echo "[ohos] ALL OHOS PLATFORM CHECKS PASSED"
