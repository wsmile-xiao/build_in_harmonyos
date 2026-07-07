#!/usr/bin/env zsh
# ============================================================
# ci/conan/cleanup.sh — CI 构建后全量还原
#
# 策略: 除关键配置外, 清理一切 CI 产生的数据。
# 由 buildbot 作为最后一个 step 执行 (alwaysRun, 在 upload/sign 之后)。
#
# 设计参考: worker-app 的 protected_paths 模型。
# 清理 $HOME 下所有非保护路径, 以及 conan cache 全量重置。
# ============================================================
set -uo pipefail

CONAN_HOME="${CONAN_HOME:-$HOME/.conan2}"
HOME_DIR="${HOME:-/storage/Users/currentUser}"
WORKDIR="${1:-$(pwd)}"

echo "[cleanup] ===== CI 构建后全量还原 ====="
echo "[cleanup] HOME: $HOME_DIR"
echo "[cleanup] CONAN_HOME: $CONAN_HOME"
echo "[cleanup] WORKDIR: $WORKDIR"

# ── 清理前快照 ──
echo ""
echo "── [0] 清理前磁盘快照 ──"
BEFORE_SIZE=$(du -sh "$HOME_DIR" 2>/dev/null | cut -f1 || echo "?")
echo "[cleanup] HOME 占用: $BEFORE_SIZE"
if [ -d "$CONAN_HOME/p" ]; then
    echo "[cleanup] conan p/ 占用: $(du -sh "$CONAN_HOME/p" 2>/dev/null | cut -f1 || echo '?')"
fi

# ════════════════════════════════════════════════════════════
# 1. CONAN CACHE 全量清理
#    conan 构建产生的所有数据都在 ~/.conan2/ 下
# ════════════════════════════════════════════════════════════
echo ""
echo "── [1] CONAN CACHE 全量清理 ──"

# 1a. 用 conan 自身命令清理 (正确更新数据库)
if command -v conan >/dev/null 2>&1; then
    echo "[cleanup] conan remove *:* ..."
    conan remove "*:*" -c 2>/dev/null || true
fi

# 1b. 物理删除所有缓存目录 (conan 可能残留 hash 目录)
# 使用 nullglob 行为: 不匹配时不报错
setopt nonomatch 2>/dev/null || true
CONAN_CLEAN_DIRS=(p s t b)
for subdir in "${CONAN_CLEAN_DIRS[@]}"; do
    if [ -d "$CONAN_HOME/$subdir" ]; then
        SIZE=$(du -sh "$CONAN_HOME/$subdir" 2>/dev/null | cut -f1 || echo "?")
        echo "[cleanup] .conan2/$subdir/ ($SIZE) → 删除"
        rm -rf "${CONAN_HOME}/${subdir}"/* 2>/dev/null || true
        rm -rf "${CONAN_HOME}/${subdir}"/.[!.]* 2>/dev/null || true
    fi
done

# 1c. 删除 cache 索引数据库 (下次 conan 运行自动重建)
CONAN_CLEAN_FILES=(cache.sqlite3 cache.sqlite3-shm cache.sqlite3-wal .conan.lock)
for f in "${CONAN_CLEAN_FILES[@]}"; do
    if [ -f "$CONAN_HOME/$f" ]; then
        echo "[cleanup] .conan2/$f → 删除"
        rm -f "$CONAN_HOME/$f" 2>/dev/null || true
    fi
done

# 1d. 重建空目录
mkdir -p "$CONAN_HOME/p" "$CONAN_HOME/s" "$CONAN_HOME/t" 2>/dev/null || true
echo "[cleanup] conan cache 目录已重建为空"

# ════════════════════════════════════════════════════════════
# 2. .conan2 下的非保护文件清理
#    保护文件 = conan 基础配置, 删除后 worker 无法工作
# ════════════════════════════════════════════════════════════
echo ""
echo "── [2] .conan2 杂项文件清理 ──"

# .conan2 下应该保留的条目 (允许清单)
CONAN_KEEP=(
    profiles settings.yml global.conf remotes.json version.txt
    migrations extensions .conan.db readers
)
# 动态生成 find 排除参数
FIND_PRUNE=""
for keep in "${CONAN_KEEP[@]}"; do
    FIND_PRUNE="$FIND_PRUNE -name $keep -o"
done
# 去掉末尾的 " -o"
FIND_PRUNE="${FIND_PRUNE% -o}"

# 清理 .conan2 下的未知文件和目录 (不在保护清单内的)
# 使用 \( \) 分组确保 -not 对整个 prune 列表生效, 避免 -o 分支导致保护文件被删除
# shellcheck disable=SC2086
STRAY_CONAN=$(find "$CONAN_HOME" -maxdepth 1 -mindepth 1 \
    -not \( $FIND_PRUNE \) 2>/dev/null || true)
if [ -n "$STRAY_CONAN" ]; then
    echo "$STRAY_CONAN" | while IFS= read -r item; do
        [ -n "$item" ] && rm -rf "$item" 2>/dev/null && echo "[cleanup] 删除杂项: $(basename "$item")"
    done
fi

# ════════════════════════════════════════════════════════════
# 3. BUILDBOT WORKDIR 构建产物清理
#    buildbot 的 clobber 模式会在下次构建前清理 workdir,
#    但我们主动清理以确保本次构建不残留。
#    workdir = $HOME/opt/buildbot-worker/<builder>/build/
# ════════════════════════════════════════════════════════════
echo ""
echo "── [3] BUILDBOT WORKDIR 清理 ──"

# 清理 workdir 下的构建产物 (保留 buildbot.tac 等在上级目录)
WORKDIR_CLEAN=(
    ".ci_logs"
    "ci-metadata.json"
    "build_and_test.log"
    "conan_build_*.log"
)
for pattern in "${WORKDIR_CLEAN[@]}"; do
    found=$(find "$WORKDIR" -maxdepth 2 -name "$pattern" 2>/dev/null || true)
    if [ -n "$found" ]; then
        echo "$found" | while IFS= read -r f; do
            [ -n "$f" ] && rm -rf "$f" 2>/dev/null && echo "[cleanup] 删除 workdir: $(basename "$f")"
        done
    fi
done

# ════════════════════════════════════════════════════════════
# 4. $HOME 下的构建散落文件扫描
#    被测代码的 make install / test 可能在 $HOME 下写入文件
# ════════════════════════════════════════════════════════════
echo ""
echo "── [4] $HOME 散落文件扫描 ──"

# $HOME 下允许存在的条目 (初始部署状态 + OHOS 系统目录)
# 如果构建过程中产生了不在清单中的文件/目录, 全部清理
HOME_KEEP=(
    # ── conan 配置 ──
    ".conan2"
    # ── CI 运行时 ──
    "opt"
    # ── shell 配置 ──
    ".bashrc" ".zshrc" ".profile"
    ".bash_profile" ".zprofile"
    ".bash_history" ".zsh_history"
    # ── OHOS 系统目录 (不可删除) ──
    "Desktop" "Documents" "Download"
    "Music" "Videos" "Images"
    "Huawei Share"
    "appdata" "tmp"
    # ── OHOS 系统隐藏目录 ──
    ".Recent" ".Trash" ".thumbs"
    ".ohos_git" ".ssh"
    # ── 基础配置/工具 ──
    ".config" ".local"
    ".ohpcd" ".hnp"
    # NOTE: ~/usr/ 不再保护 — make install 可能写入未签名的 .so 污染环境
)

# 扫描 $HOME 下的顶层条目, 清理不在保护清单内的
HOME_STRAY=""
for item in "$HOME_DIR"/* "$HOME_DIR"/.[!.]*; do
    [ -e "$item" ] || continue
    base=$(basename "$item")
    skip=false
    for keep in "${HOME_KEEP[@]}"; do
        [ "$base" = "$keep" ] && skip=true && break
    done
    if [ "$skip" = false ]; then
        HOME_STRAY="${HOME_STRAY}${HOME_STRAY:+$'\n'}${item}"
    fi
done

if [ -n "$HOME_STRAY" ]; then
    echo "[cleanup] 发现 $HOME 下散落文件:"
    echo "$HOME_STRAY" | while IFS= read -r item; do
        [ -n "$item" ] || continue
        SIZE=$(du -sh "$item" 2>/dev/null | cut -f1 || echo "?")
        echo "[cleanup]   $(basename "$item") ($SIZE) → 删除"
        rm -rf "$item" 2>/dev/null || true
    done
else
    echo "[ok] $HOME 下无散落文件"
fi

# ════════════════════════════════════════════════════════════
# 5. 其他常见缓存/临时目录清理
# ════════════════════════════════════════════════════════════
echo ""
echo "── [5] 缓存/临时目录清理 ──"

# ccache (如果构建系统启用了)
if [ -d "$HOME_DIR/.ccache" ]; then
    SIZE=$(du -sh "$HOME_DIR/.ccache" 2>/dev/null | cut -f1 || echo "?")
    echo "[cleanup] .ccache ($SIZE) → 清空"
    rm -rf "${HOME_DIR}/.ccache"/* 2>/dev/null || true
fi

# pip cache (如果 conanfile 中用了 pip)
if [ -d "$HOME_DIR/.cache/pip" ]; then
    SIZE=$(du -sh "$HOME_DIR/.cache/pip" 2>/dev/null | cut -f1 || echo "?")
    echo "[cleanup] .cache/pip ($SIZE) → 清空"
    rm -rf "${HOME_DIR}/.cache/pip"/* 2>/dev/null || true
fi

# conan 可能用到的系统 temp 目录 (OHOS 上可能不存在 /tmp)
for tmpdir in "/tmp" "/var/tmp" "$HOME_DIR/.tmp"; do
    if [ -d "$tmpdir" ] && [ -w "$tmpdir" ]; then
        # 只清理 conan 相关的临时文件
        conan_tmp=$(find "$tmpdir" -maxdepth 1 -name "conan*" -o -name "tmp*" 2>/dev/null | head -20)
        if [ -n "$conan_tmp" ]; then
            echo "$conan_tmp" | while IFS= read -r f; do
                [ -n "$f" ] && rm -rf "$f" 2>/dev/null
            done
            echo "[cleanup] $tmpdir/conan* 临时文件已清理"
        fi
    fi
done

# ════════════════════════════════════════════════════════════
# 6. 配置完整性校验
# ════════════════════════════════════════════════════════════
echo ""
echo "── [6] 配置完整性校验 ──"

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
    "$HOME_DIR/opt/buildbot-worker/buildbot.tac"
)

ALL_OK=true
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "  [ok] $(basename "$f")"
    else
        echo "  [WARN] $(basename "$f") 缺失!"
        ALL_OK=false
    fi
done
for d in "${REQUIRED_DIRS[@]}"; do
    if [ -e "$d" ]; then
        echo "  [ok] $(basename "$d")"
    else
        echo "  [WARN] $(basename "$d") 缺失!"
        ALL_OK=false
    fi
done

# ════════════════════════════════════════════════════════════
# 7. 总结
# ════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════════"
echo " 全量还原完成"
echo "══════════════════════════════════════════════"

AFTER_SIZE=$(du -sh "$HOME_DIR" 2>/dev/null | cut -f1 || echo "?")
echo ""
echo "磁盘: ${BEFORE_SIZE} → ${AFTER_SIZE} (HOME)"

if [ "$ALL_OK" = true ]; then
    echo "[ok] 所有关键配置完好, 环境已还原到初始状态"
    exit 0
else
    echo "[WARN] 部分配置缺失, 但不影响下次构建"
    exit 0  # cleanup 失败不阻塞 CI
fi
