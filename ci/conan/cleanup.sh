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
CLEANUP_INTERRUPTED=""

signal_background_command() {
    local signal_name="$1"
    local command_pid="$2"
    local command_grouped="$3"

    if [ "$command_grouped" = true ]; then
        kill -s "$signal_name" -- "-$command_pid" 2>/dev/null || true
    fi
    kill -s "$signal_name" "$command_pid" 2>/dev/null || true
}

background_command_alive() {
    local command_pid="$1"
    local command_grouped="$2"

    if [ "$command_grouped" = true ]; then
        kill -0 -- "-$command_pid" 2>/dev/null && return 0
    fi
    kill -0 "$command_pid" 2>/dev/null
}

run_with_heartbeat() {
    local label="$1"
    shift

    local setsid_command=""
    local zsh_command=""
    local command_grouped=false
    if command -v setsid >/dev/null 2>&1; then
        setsid_command=$(command -v setsid)
    elif [ -x /usr/bin/setsid ]; then
        setsid_command=/usr/bin/setsid
    fi
    if command -v zsh >/dev/null 2>&1; then
        zsh_command=$(command -v zsh)
    elif [ -x /usr/bin/zsh ]; then
        zsh_command=/usr/bin/zsh
    fi

    if [ -z "$setsid_command" ] || [ -z "$zsh_command" ]; then
        echo "[cleanup] process-group tools unavailable; running without heartbeat: $label"
        "$@"
        return $?
    fi
    if [ "${SETSID_WAIT_AVAILABLE:-unknown}" = unknown ]; then
        if "$setsid_command" -w "$zsh_command" -c 'exit 0' cleanup-probe \
                >/dev/null 2>&1; then
            SETSID_WAIT_AVAILABLE=true
        else
            SETSID_WAIT_AVAILABLE=false
        fi
    fi
    if [ "$SETSID_WAIT_AVAILABLE" != true ]; then
        echo "[cleanup] setsid -w unavailable; running without heartbeat: $label"
        "$@"
        return $?
    fi

    local temp_root="${TMPDIR:-$HOME_DIR/tmp}"
    mkdir -p "$temp_root" 2>/dev/null || {
        echo "[cleanup] heartbeat state directory unavailable; running directly: $label"
        "$@"
        return $?
    }
    local pid_file
    pid_file=$(mktemp "$temp_root/cleanup-pgid.XXXXXX") || {
        "$@"
        return $?
    }

    local command_pid=""
    local launcher_pid=""
    local elapsed=0
    local forwarded_signal=""
    local signal_elapsed=0
    local kill_sent=false
    local startup_rc=1
    local heartbeat_interval="${CLEANUP_HEARTBEAT_SECONDS:-30}"
    local signal_grace="${HEARTBEAT_SIGNAL_GRACE_SECONDS:-5}"

    [ "$heartbeat_interval" -gt 0 ] 2>/dev/null || heartbeat_interval=30
    [ "$signal_grace" -gt 0 ] 2>/dev/null || signal_grace=5

    trap 'forwarded_signal=HUP; [ -z "$command_pid" ] || signal_background_command HUP "$command_pid" "$command_grouped"' HUP
    trap 'forwarded_signal=INT; [ -z "$command_pid" ] || signal_background_command INT "$command_pid" "$command_grouped"' INT
    trap 'forwarded_signal=TERM; [ -z "$command_pid" ] || signal_background_command TERM "$command_pid" "$command_grouped"' TERM

    "$setsid_command" -w "$zsh_command" -c '
        pid_file="$1"
        shift
        print -r -- "$$" > "$pid_file" || exit 125
        exec "$@"
    ' cleanup-heartbeat "$pid_file" "$@" &
    launcher_pid=$!
    command_grouped=true
    for attempt in 1 2 3 4 5; do
        [ -s "$pid_file" ] && break
        sleep 1
    done
    if [ ! -s "$pid_file" ]; then
        signal_background_command TERM "$launcher_pid" false
        wait "$launcher_pid" 2>/dev/null || true
        trap - HUP INT TERM
        rm -f "$pid_file" 2>/dev/null || true
        case "$forwarded_signal" in
            HUP) startup_rc=129 ;;
            INT) startup_rc=130 ;;
            TERM) startup_rc=143 ;;
        esac
        return "$startup_rc"
    fi
    command_pid=$(<"$pid_file")
    if [[ "$command_pid" != <-> ]]; then
        signal_background_command TERM "$launcher_pid" false
        wait "$launcher_pid" 2>/dev/null || true
        trap - HUP INT TERM
        rm -f "$pid_file" 2>/dev/null || true
        case "$forwarded_signal" in
            HUP) startup_rc=129 ;;
            INT) startup_rc=130 ;;
            TERM) startup_rc=143 ;;
        esac
        return "$startup_rc"
    fi
    if [ -n "$forwarded_signal" ]; then
        signal_background_command "$forwarded_signal" "$command_pid" "$command_grouped"
    fi

    while background_command_alive "$command_pid" "$command_grouped"; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ -n "$forwarded_signal" ]; then
            signal_elapsed=$((signal_elapsed + 1))
            if [ "$signal_elapsed" -ge "$signal_grace" ] && \
                    [ "$kill_sent" = false ]; then
                signal_background_command KILL "$command_pid" "$command_grouped"
                kill_sent=true
            fi
        fi
        if [ $((elapsed % heartbeat_interval)) -eq 0 ] && \
                background_command_alive "$command_pid" "$command_grouped"; then
            echo "[cleanup] ${label} still in progress (${elapsed}s)..."
        fi
    done
    local launcher_rc=0
    wait "$launcher_pid" || launcher_rc=$?
    trap - HUP INT TERM

    case "$forwarded_signal" in
        HUP) rm -f "$pid_file" 2>/dev/null || true; return 129 ;;
        INT) rm -f "$pid_file" 2>/dev/null || true; return 130 ;;
        TERM) rm -f "$pid_file" 2>/dev/null || true; return 143 ;;
    esac

    rm -f "$pid_file" 2>/dev/null || true
    return "$launcher_rc"
}

run_cleanup_step() {
    run_with_heartbeat "$@"
    local command_rc=$?

    if [ "$command_rc" -ge 128 ]; then
        echo "[cleanup] interrupted while running: $1"
        if [ -z "$CLEANUP_INTERRUPTED" ]; then
            CLEANUP_INTERRUPTED="$command_rc"
        fi
        return 1
    fi
    return 0
}

normalize_existing_path() {
    local candidate_path="$1"
    local resolved_path
    local parent
    local base
    local parent_real

    if [ -L "$candidate_path" ]; then
        if command -v realpath >/dev/null 2>&1; then
            resolved_path=$(realpath "$candidate_path" 2>/dev/null) || return 1
        elif command -v readlink >/dev/null 2>&1; then
            resolved_path=$(readlink -f "$candidate_path" 2>/dev/null) || return 1
        else
            return 1
        fi
        [ -n "$resolved_path" ] || return 1
        candidate_path="$resolved_path"
    fi

    if [ -d "$candidate_path" ]; then
        (cd "$candidate_path" 2>/dev/null && pwd -P)
        return
    fi

    [ -e "$candidate_path" ] || return 1
    parent=$(dirname "$candidate_path")
    base=$(basename "$candidate_path")
    parent_real=$(cd "$parent" 2>/dev/null && pwd -P) || return 1
    echo "${parent_real}/${base}"
}

path_is_within() {
    local candidate_path="$1"
    local root="$2"

    case "$candidate_path" in
        "$root"|"$root"/*) return 0 ;;
        *) return 1 ;;
    esac
}

find_worker_root() {
    local current="$1"
    local home_root="$2"

    while path_is_within "$current" "$home_root"; do
        if [ -f "$current/buildbot.tac" ]; then
            echo "$current"
            return 0
        fi
        [ "$current" = "$home_root" ] && break
        current="${current:h}"
    done
    return 1
}

is_protected_home_item() {
    local item_real
    local protected

    item_real=$(normalize_existing_path "$1") || return 0
    for protected in "${PROTECTED_HOME_PATHS[@]}"; do
        case "$protected" in
            "$item_real"|"$item_real"/*) return 0 ;;
        esac
    done
    return 1
}

HOME_REAL=$(normalize_existing_path "$HOME_DIR") || HOME_REAL=""
WORKDIR_REAL=$(normalize_existing_path "$WORKDIR") || WORKDIR_REAL=""
WORKER_ROOT_REAL=""
if [ -n "$HOME_REAL" ] && [ -n "$WORKDIR_REAL" ]; then
    WORKER_ROOT_REAL=$(find_worker_root "$WORKDIR_REAL" "$HOME_REAL") || WORKER_ROOT_REAL=""
fi

PROTECTED_HOME_PATHS=()
for protected_path in \
    "$CONAN_HOME" "$WORKDIR_REAL" "$WORKER_ROOT_REAL" \
    "$HOME_DIR/.gitconfig" "$HOME_DIR/.gitcode-token"; do
    [ -n "$protected_path" ] || continue
    protected_real=$(normalize_existing_path "$protected_path") || continue
    PROTECTED_HOME_PATHS+=("$protected_real")
done

HOME_SCAN_SAFE=true
if [ -z "$HOME_REAL" ] || [ -z "$WORKDIR_REAL" ] || \
        [ -z "$WORKER_ROOT_REAL" ] || \
        ! path_is_within "$WORKDIR_REAL" "$HOME_REAL"; then
    HOME_SCAN_SAFE=false
fi

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
    run_cleanup_step "conan remove" conan remove "*:*" -c 2>/dev/null
fi

# 1b. 物理删除所有缓存目录 (conan 可能残留 hash 目录)
# 使用 nullglob 行为: 不匹配时不报错
setopt nonomatch 2>/dev/null || true
CONAN_CLEAN_DIRS=(p s t b)
for subdir in "${CONAN_CLEAN_DIRS[@]}"; do
    if [ -d "$CONAN_HOME/$subdir" ]; then
        SIZE=$(du -sh "$CONAN_HOME/$subdir" 2>/dev/null | cut -f1 || echo "?")
        echo "[cleanup] .conan2/$subdir/ ($SIZE) → 删除"
        run_cleanup_step ".conan2/${subdir}/ deletion" \
            rm -rf "${CONAN_HOME}/${subdir}"/* "${CONAN_HOME}/${subdir}"/.[!.]* \
            2>/dev/null
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
    # ── 持久 Git/GitCode 凭据 ──
    ".gitconfig" ".gitcode-token"
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
if [ "$HOME_SCAN_SAFE" = false ]; then
    echo "[WARN] HOME/workdir path normalization failed; skipping HOME deletion"
else
    for item in "$HOME_DIR"/* "$HOME_DIR"/.[!.]*; do
        [ -e "$item" ] || continue
        base=$(basename "$item")
        skip=false
        for keep in "${HOME_KEEP[@]}"; do
            [ "$base" = "$keep" ] && skip=true && break
        done
        if [ "$skip" = false ] && is_protected_home_item "$item"; then
            skip=true
        fi
        if [ "$skip" = false ]; then
            HOME_STRAY="${HOME_STRAY}${HOME_STRAY:+$'\n'}${item}"
        fi
    done
fi

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
        conan_tmp=$(find "$tmpdir" -maxdepth 1 \( -name "conan*" -o -name "tmp*" \) 2>/dev/null | head -20 || true)
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

if [ -n "$CLEANUP_INTERRUPTED" ]; then
    echo "[cleanup] completed remaining cleanup after interruption (rc=$CLEANUP_INTERRUPTED)"
    exit "$CLEANUP_INTERRUPTED"
elif [ "$ALL_OK" = true ]; then
    echo "[ok] 所有关键配置完好, 环境已还原到初始状态"
    exit 0
else
    echo "[WARN] 部分配置缺失, 但不影响下次构建"
    exit 0  # cleanup 失败不阻塞 CI
fi
