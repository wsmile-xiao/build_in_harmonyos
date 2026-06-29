#!/usr/bin/env zsh
# ============================================================
# ci/conan/cleanup.sh — CI 构建后全量还原
#
# 清理所有 conan 构建产生的数据, 保留基础配置, 回到初始部署状态。
# 由 buildbot 作为最后一个 step 执行 (alwaysRun, 在 upload 之后)。
#
# 清理内容:
#   ~/.conan2/p/         → 包缓存 (二进制 + 源码)
#   ~/.conan2/s/         → 源码缓存
#   ~/.conan2/cache.sqlite3 → cache 索引数据库
#   buildbot workdir/.ci_logs → 构建日志
#
# 保留内容:
#   ~/.conan2/profiles/      → OHOS 构建配置
#   ~/.conan2/settings.yml   → OHOS 平台设置
#   ~/.conan2/global.conf    → conan 全局配置
#   ~/.conan2/remotes.json   → 远程仓库地址
#   ~/.conan2/.conan.db      → REL 模式凭证 (CI 模式无此文件)
#   ~/.conan2/extensions/    → conan 扩展
#   ~/.conan2/migrations/    → 数据库迁移
#   ~/.conan2/version.txt    → 版本标记
# ============================================================
set -uo pipefail

CONAN_HOME="${CONAN_HOME:-$HOME/.conan2}"
CLEANED_SIZE=0

echo "[cleanup] 开始全量还原..."
echo "[cleanup] CONAN_HOME: $CONAN_HOME"

# ── 1. 清理 conan cache ──
echo ""
echo "── [1] conan cache 清理 ──"

if [ -d "$CONAN_HOME/p" ]; then
    CACHE_SIZE=$(du -sh "$CONAN_HOME/p" 2>/dev/null | cut -f1)
    echo "[cleanup] 包缓存 (p/) 占用: ${CACHE_SIZE}"
    rm -rf "${CONAN_HOME}/p/"*
    echo "[cleanup] 包缓存已清空"
else
    echo "[cleanup] 包缓存目录不存在, 跳过"
fi

if [ -d "$CONAN_HOME/s" ]; then
    SRC_SIZE=$(du -sh "$CONAN_HOME/s" 2>/dev/null | cut -f1)
    echo "[cleanup] 源码缓存 (s/) 占用: ${SRC_SIZE}"
    rm -rf "${CONAN_HOME}/s/"*
    echo "[cleanup] 源码缓存已清空"
else
    echo "[cleanup] 源码缓存目录不存在, 跳过"
fi

# 删除 cache 索引数据库 (下次 conan 运行时自动重建)
if [ -f "$CONAN_HOME/cache.sqlite3" ]; then
    rm -f "$CONAN_HOME/cache.sqlite3"
    echo "[cleanup] cache 索引数据库已删除 (下次运行自动重建)"
fi

# ── 2. 用 conan 自身命令做最终确认 ──
echo ""
echo "── [2] conan remove 确认 ──"
if command -v conan >/dev/null 2>&1; then
    # 二次确认: 用 conan 命令清理可能的数据库残留引用
    conan remove "*:*" -c 2>/dev/null || true
    echo "[cleanup] conan remove 确认完成"
else
    echo "[cleanup] conan 命令不可用, 跳过"
fi

# ── 3. 清理构建日志 ──
echo ""
echo "── [3] 构建日志清理 ──"

# .ci_logs 在 buildbot workdir 中
WORKDIR="${1:-$(pwd)}"
if [ -d "$WORKDIR/.ci_logs" ]; then
    LOG_SIZE=$(du -sh "$WORKDIR/.ci_logs" 2>/dev/null | cut -f1)
    echo "[cleanup] .ci_logs 占用: ${LOG_SIZE}"
    rm -rf "$WORKDIR/.ci_logs"
    echo "[cleanup] .ci_logs 已清理"
fi

# ── 4. 清理 conan 可能的临时文件 ──
echo ""
echo "── [4] conan 临时文件清理 ──"

# conan 2.x 可能在 .conan2/t/ 目录留临时文件
if [ -d "$CONAN_HOME/t" ]; then
    rm -rf "${CONAN_HOME}/t/"*
    echo "[cleanup] conan 临时目录已清理"
fi

# ── 5. 验证保留的配置文件 ──
echo ""
echo "── [5] 配置文件完整性检查 ──"

REQUIRED_FILES=(
    "$CONAN_HOME/settings.yml"
    "$CONAN_HOME/global.conf"
    "$CONAN_HOME/remotes.json"
    "$CONAN_HOME/version.txt"
)
REQUIRED_DIRS=(
    "$CONAN_HOME/profiles"
    "$CONAN_HOME/extensions"
    "$CONAN_HOME/migrations"
)

ALL_OK=true
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "[ok] $(basename "$f")"
    else
        echo "[WARN] $(basename "$f") 缺失!"
        ALL_OK=false
    fi
done
for d in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$d" ]; then
        echo "[ok] $(basename "$d")/"
    else
        echo "[WARN] $(basename "$d")/ 缺失!"
        ALL_OK=false
    fi
done

# ── 6. 总结 ──
echo ""
echo "══════════════════════════════════════"
echo " 全量还原完成"
echo "══════════════════════════════════════"
echo ""
echo "conan cache 状态:"
# 重建空目录
mkdir -p "$CONAN_HOME/p" 2>/dev/null || true

if [ "$ALL_OK" = true ]; then
    echo "[ok] 所有关键配置文件完好"
    echo "[ok] 环境已还原到初始部署状态"
else
    echo "[WARN] 部分配置文件缺失, 下次构建可能需要重新初始化"
fi
echo ""
echo "磁盘占用:"
du -sh "$CONAN_HOME" 2>/dev/null || echo "(无法计算)"
