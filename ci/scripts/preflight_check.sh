#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# preflight_check.sh — 适配前预检工具 (W0 + R35 + R36)
#
# 用途: 在开始适配任何软件之前，检查其所有依赖是否已发布到制品仓。
#       如果有依赖未发布，给出清晰的发布顺序建议。
#
# 用法:
#   bash ci/scripts/preflight_check.sh <软件名>/<版本>
#   bash ci/scripts/preflight_check.sh zlib/1.3.1
#
# 如果 conanfile.py 尚未生成，可以用 --deps 手动指定依赖:
#   bash ci/scripts/preflight_check.sh <软件名>/<版本> --deps "openssl/3.0.0 zlib/1.3.1"
#
# 退出码:
#   0 = 所有依赖已发布，可以安全适配
#   1 = 有依赖未发布，需要先适配并发布依赖
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"
ARCHIVES_ROOT="${ARCHIVES_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)/archives}"

print_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_fail() { echo -e "${RED}[FAIL]${NC} $1"; }
print_info() { echo -e "${CYAN}[INFO]${NC} $1"; }

# ── 参数解析 ──
if [ $# -lt 1 ]; then
    echo "Usage: bash ci/scripts/preflight_check.sh <软件名>/<版本> [--deps \"dep1/ver1 dep2/ver2\"]"
    echo ""
    echo "Examples:"
    echo "  bash ci/scripts/preflight_check.sh zlib/1.3.1"
    echo "  bash ci/scripts/preflight_check.sh mypkg/1.0.0 --deps \"openssl/3.0.0 zlib/1.3.1\""
    exit 1
fi

PKG_REF="$1"
shift

MANUAL_DEPS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --deps)
            MANUAL_DEPS="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  适配前预检: ${PKG_REF}"
echo "  制品仓: ${REMOTE_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 提取依赖列表 ──
DEPS=""

if [ -n "$MANUAL_DEPS" ]; then
    # 手动指定
    DEPS="$MANUAL_DEPS"
elif [ -d "${ARCHIVES_ROOT}" ]; then
    # 从 conanfile.py 中提取
    # 尝试找到对应的 conanfile.py
    PKG_NAME="${PKG_REF%%/*}"
    FIRST_LETTER="$(echo "${PKG_NAME}" | cut -c1)"
    CONANFILE="${ARCHIVES_ROOT}/${FIRST_LETTER}/${PKG_NAME}/${PKG_REF#*/}/conanfile.py"

    if [ ! -f "$CONANFILE" ]; then
        # 尝试在 staging 或其他位置查找
        CONANFILE=$(find "${ARCHIVES_ROOT}" -path "*/${PKG_NAME}/*/conanfile.py" -print -quit 2>/dev/null)
    fi

    if [ -f "$CONANFILE" ] && command -v python3 >/dev/null 2>&1; then
        DEPS=$(python3 - "$CONANFILE" 2>/dev/null <<'PYEOF'
import re, sys
src = open(sys.argv[1]).read()
refs = set()
for m in re.finditer(r'(?:self\.)?requires?\s*\(\s*["\']([^"\']+)["\']', src):
    ref = m.group(1).strip()
    if '/' not in ref:
        continue
    ref = ref.split('@')[0]  # 兼容性: 去掉可能的 @user/channel 后缀
    refs.add(ref)
for m in re.finditer(r'tool_requires?\s*\(\s*["\']([^"\']+)["\']', src):
    ref = m.group(1).strip()
    if '/' not in ref:
        continue
    ref = ref.split('@')[0]
    refs.add(ref)
for r in sorted(refs):
    print(r)
PYEOF
)
    fi
fi

if [ -z "$DEPS" ]; then
    print_info "未找到依赖声明（conanfile.py 尚未生成或无依赖）。"
    print_info "如果是首次适配，这是正常的。适配生成 conanfile.py 后可再次运行检查。"
    echo ""
    print_ok "预检通过（无依赖需要检查）"
    exit 0
fi

# ── 逐个检查依赖 ──
print_info "发现 $(echo "$DEPS" | wc -w) 个依赖，开始检查发布状态..."
echo ""

UNPUBLISHED=""
PUBLISHED=""

for dep in $DEPS; do
    # R35: 用 conan download --recipe 验证（禁止用 conan list）
    if conan download "$dep" -r="${REMOTE_NAME}" --only-recipe >/dev/null 2>&1; then
        print_ok "已发布: ${dep}"
        PUBLISHED="${PUBLISHED} ${dep}"
    else
        print_warn "未发布: ${dep}"
        UNPUBLISHED="${UNPUBLISHED} ${dep}"
    fi
done

# ── 版本号占用检查 (R37) ──
echo ""
print_info "检查版本号是否已被占用 (R37)..."
if conan download "${PKG_REF}" -r="${REMOTE_NAME}" --only-recipe >/dev/null 2>&1; then
    # 制品仓中已存在该版本, 检查 conanfile.py 是否有修改
    REMOTE_CACHE_DIR=$(conan cache path "${PKG_REF}" 2>/dev/null || echo "")
    if [ -n "$REMOTE_CACHE_DIR" ] && [ -f "$CONANFILE" ] && [ -f "$REMOTE_CACHE_DIR/conanfile.py" ]; then
        if diff -q "$CONANFILE" "$REMOTE_CACHE_DIR/conanfile.py" >/dev/null 2>&1; then
            print_ok "版本号已发布, conanfile.py 未修改: ${PKG_REF}"
        else
            print_fail "版本号 ${PKG_REF} 已发布, 但 conanfile.py 有修改 (R37)"
            echo ""
            echo -e "  ${RED}cnb.cool 制品仓不支持同版本多 revision 并存${NC}"
            echo -e "  ${YELLOW}请递增版本号后缀:${NC}"
            BASE_VER="${PKG_REF#*/}"
            echo "    ${PKG_REF} → ${PKG_REF%%/*}/${BASE_VER}.1"
            echo ""
            exit 1
        fi
    else
        print_warn "版本号已发布: ${PKG_REF} (无法比较 conanfile.py, 请确认是否有修改)"
    fi
else
    print_ok "版本号未被占用: ${PKG_REF}"
fi

# ── 结果汇总 ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -z "$UNPUBLISHED" ]; then
    print_ok "所有依赖均已发布到制品仓，可以安全开始适配 ${PKG_REF}"
    echo ""
    exit 0
else
    print_fail "有 $(echo "$UNPUBLISHED" | wc -w) 个依赖未发布！"
    echo ""
    echo -e "${YELLOW}未发布的依赖:${NC}"
    for d in $UNPUBLISHED; do
        dep_short=$(echo "$d" | sed 's/@.*//')
        echo "  - ${dep_short}"
    done
    echo ""
    echo -e "${CYAN}建议操作 (R36: 依赖发布优先级):${NC}"
    echo "  1. 先适配并发布以上依赖包（走完整适配→CI→release 流程）"
    echo "  2. 依赖发布成功后，再回来适配 ${PKG_REF}"
    echo "  3. 多层依赖链（如 C→B→A）按拓扑序从最底层开始逐层发布"
    echo ""
    echo -e "${YELLOW}快捷命令:${NC}"
    for d in $UNPUBLISHED; do
        dep_short=$(echo "$d" | sed 's@/.*@@')
        echo "  bash ci/scripts/preflight_check.sh ${dep_short}/<版本>"
    done
    echo ""
    exit 1
fi
