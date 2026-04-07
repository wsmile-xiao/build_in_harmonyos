#!/bin/sh
# search-download-url.sh — URL 搜索辅助工具（Layer 3）
# 用法: ./scripts/search-download-url.sh <软件名> [版本]
#
# 当 software-registry.yaml 中没有 URL 时，AI 调用此工具
# 搜索候选下载 URL 并返回列表供 AI 选择。
#
# Layer: Layer3（辅助工具，供 AI 调用）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="${SCRIPT_DIR}/software-registry.yaml"

if [ $# -lt 1 ]; then
    echo "用法: $0 <软件名> [版本]"
    exit 1
fi

NAME="$1"
VERSION="${2:-latest}"

echo "🔍 搜索 ${NAME} ${VERSION} 的下载 URL..."
echo ""

# ---- 策略 1: GNU FTP ----
echo "=== [策略 1/5] GNU FTP ==="
GNU_URL="https://ftp.gnu.org/gnu/${NAME}/${NAME}-${VERSION}.tar"
for ext in gz xz bz2; do
    URL="https://ftp.gnu.org/gnu/${NAME}/${NAME}-${VERSION}.tar.${ext}"
    HTTP_CODE=$(curl -sI --connect-timeout 5 "$URL" 2>/dev/null | head -1 | tr -d '\r' | awk '{print $2}')
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
        echo "  ✅ ${URL} (HTTP ${HTTP_CODE})"
    fi
done

# ---- 策略 2: GitHub Releases ----
echo ""
echo "=== [策略 2/5] GitHub Releases ==="
# 常见的 GitHub org 映射
for ORG_REPO in \
    "${NAME}/${NAME}" \
    "gnu-${name}/${name}" \
    "${name}-project/${name}" \
    "lib${name}/lib${name}"; do
    URL="https://github.com/${ORG_REPO}/releases/download/v${VERSION}/${NAME}-${VERSION}.tar.gz"
    HTTP_CODE=$(curl -sI --connect-timeout 5 "$URL" 2>/dev/null | head -1 | tr -d '\r' | awk '{print $2}')
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
        echo "  ✅ ${URL} (HTTP ${HTTP_CODE})"
    fi
done

# ---- 策略 3: freedesktop / savannah ----
echo ""
echo "=== [策略 3/5] freedesktop / Savannah ==="
for BASE in \
    "https://${NAME}.freedesktop.org/releases" \
    "https://${NAME}.io/files" \
    "https://download.savannah.nongnu.org/releases/${NAME}" \
    "https://${NAME}.home.xs4all.nl"; do
    for ext in gz xz; do
        URL="${BASE}/${NAME}-${VERSION}.tar.${ext}"
        HTTP_CODE=$(curl -sI --connect-timeout 5 "$URL" 2>/dev/null | head -1 | tr -d '\r' | awk '{print $2}')
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
            echo "  ✅ ${URL} (HTTP ${HTTP_CODE})"
        fi
    done
done

# ---- 策略 4: 项目官网常见路径 ----
echo ""
echo "=== [策略 4/5] 官方站点 ==="
for BASE in \
    "https://www.${NAME}.org" \
    "https://${NAME}.org" \
    "https://tukaani.org/${NAME}" \
    "https://www.zlib.net" \
    "https://astron.com/pub/${NAME}" \
    "https://waterlan.home.xs4all.nl/${NAME}"; do
    for ext in gz xz; do
        URL="${BASE}/${NAME}-${VERSION}.tar.${ext}"
        HTTP_CODE=$(curl -sI --connect-timeout 5 "$URL" 2>/dev/null | head -1 | tr -d '\r' | awk '{print $2}')
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
            echo "  ✅ ${URL} (HTTP ${HTTP_CODE})"
        fi
    done
done

# ---- 策略 5: DuckDuckGo 搜索 ----
echo ""
echo "=== [策略 5/5] 搜索引擎 ==="
if command -v curl >/dev/null 2>&1; then
    # 输出搜索建议供 AI 使用
    echo "  💡 建议使用搜索引擎查找:"
    echo "     duckduckgo \"${NAME} ${VERSION} download source tarball\""
    echo "     或在浏览器中访问:"
    echo "     https://duckduckgo.com/?q=${NAME}+${VERSION}+download+source+tarball"
fi

echo ""
echo "═════════════════════════════"
echo "请从以上 ✅ 标记的 URL 中选择一个"
echo "然后执行: ./scripts/init-build.sh ${NAME} ${VERSION} --url=<选中的URL>"
echo "═════════════════════════════"
