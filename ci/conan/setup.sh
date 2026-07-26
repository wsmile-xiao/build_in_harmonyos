#!/usr/bin/zsh
# ci/conan/setup.sh — Conan environment initialization
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=success, non-0=failure (blocks subsequent steps)
# Timeout: 20 minutes
#
# Must complete:
#   - Detect/install Conan (pip install conan)
#   - Verify conan remote (预部署, 不做注册/认证)
#   - Ensure ohos-aarch64 profile exists
#   - Set conan configuration

set -euo pipefail

# ── Path resolution ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

echo "[step] Conan environment setup..."

# ── 1. Detect/install Conan ──
# pip3 可能装到 ~/.local/bin, 确保在 PATH 上
export PATH="$HOME/.local/bin:$PATH"

# Check both that conan exists AND is functional (conan --version succeeds)
# If conan binary exists but is broken, force-reinstall to fix
if ! command -v conan &>/dev/null || ! conan --version &>/dev/null; then
    echo "[step] Conan not found or broken, (re)installing..."
    # 安装 OHOS 适配版 conan（私有 PyPI 提供，基线 2.29.1，已适配 OHOS 平台）
    # 不要钉死官方旧版本号，应从配置的 PyPI 源安装最新适配版
    # Use python3 -m pip to bypass potentially broken pip3 shebang
    # (HNP pip3/conan binaries may have shebangs pointing to non-existent
    #  build-machine paths with ^M line endings)
    python3 -m pip install --user --force-reinstall conan || {
        echo "[error] Failed to install conan"
        exit 1
    }
    # Ensure user-installed binaries are found before any broken HNP version
    export PATH="$HOME/.local/bin:$PATH"
fi

CONAN_VERSION=$(conan --version 2>/dev/null || echo "unknown")
echo "[step] Conan version: $CONAN_VERSION"

# If conan still can't run after install/reinstall, diagnose the root cause
if [ "$CONAN_VERSION" = "unknown" ]; then
    echo "[error] conan 仍然无法运行, 诊断系统环境..."
    # Check for common system-level issues
    python3 -c "import sqlite3" 2>&1 || {
        echo "[error] Python sqlite3 模块损坏 — libsqlite3.so.0 缺失"
        echo "[error] 这不是 conan 问题, 需要在 Worker 上安装/链接 libsqlite3.so.0"
        echo "[error] 修复: 找到 HNP 目录下的 libsqlite3.so.0 或从 OHOS 系统链接"
        # Try to find and link it
        SQLITE_LIB=$(find /data/service/hnp /system/lib* /usr/lib* -name 'libsqlite3.so*' 2>/dev/null | head -1)
        if [ -n "$SQLITE_LIB" ]; then
            echo "[step] 尝试设置 LD_LIBRARY_PATH: $(dirname "$SQLITE_LIB")"
            export LD_LIBRARY_PATH="$(dirname "$SQLITE_LIB"):${LD_LIBRARY_PATH:-}"
            CONAN_VERSION=$(conan --version 2>/dev/null || echo "unknown")
            echo "[step] Retry conan version: $CONAN_VERSION"
        fi
    }
    python3 -c "import ssl" 2>&1 || echo "[error] Python ssl 模块损坏 — libssl.so 缺失"
    # Check for other missing shared libraries
    PYTHON3_BIN=$(which python3 2>/dev/null)
    if [ -n "$PYTHON3_BIN" ]; then
        ldd "$PYTHON3_BIN" 2>/dev/null | grep "not found" | while read -r line; do
            echo "[error] 缺失动态库: $line"
        done
    fi
    # Final check — if still broken, exit with clear message
    if [ "$CONAN_VERSION" = "unknown" ]; then
        echo "[error] Conan 无法启动, Worker 环境需要修复 (非 CI 脚本问题)"
        exit 1
    fi
fi

# ── 1b. Refresh stale settings.yml ──
# conan caches settings.yml on first run; if conan was upgraded (e.g. OHOS
# support added to default_settings.py), the cached file is stale and
# conan will reject os=OHOS. Delete it to force regeneration.
CONAN_HOME="${CONAN_HOME:-$HOME/.conan2}"
SETTINGS_FILE="$CONAN_HOME/settings.yml"
if [ -f "$SETTINGS_FILE" ]; then
    if ! grep -q "OHOS" "$SETTINGS_FILE" 2>/dev/null; then
        echo "[step] Refreshing stale settings.yml (missing OHOS enum)"
        rm -f "$SETTINGS_FILE" "$SETTINGS_FILE.orig"
    fi
fi

# ── 2. Conan remote (自动初始化, 兼容 CI 机/发布机) ──
# CI 机 .conan.db 无 remote 定义 → 自动添加(匿名读取)
# 发布机已有同名 remote + token → 跳过, 不影响 upload 凭证
CONAN_REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"
CONAN_REMOTE_URL="${CONAN_REMOTE_URL:-https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/}"

# Disable conancenter — these are private CI builds, no external deps needed
if conan remote list 2>/dev/null | grep -q "^conancenter:"; then
    echo "[step] Disabling conancenter (private CI, not needed)"
    conan remote disable conancenter 2>/dev/null || true
fi

if conan remote list 2>/dev/null | grep -q "^${CONAN_REMOTE_NAME}:"; then
    echo "[step] remote 已就绪: ${CONAN_REMOTE_NAME}"
else
    echo "[step] remote '${CONAN_REMOTE_NAME}' 不存在, 自动添加 (匿名读取)"
    conan remote add "${CONAN_REMOTE_NAME}" "${CONAN_REMOTE_URL}" || {
        echo "[error] 无法添加 remote '${CONAN_REMOTE_NAME}'"
        exit 1
    }
    echo "[step] remote 已添加: ${CONAN_REMOTE_NAME} → ${CONAN_REMOTE_URL}"
fi

# ── 3. Ensure ohos-aarch64 profile exists ──
PROFILE_NAME="${CONAN_PROFILE:-ohos-aarch64}"
PROFILE_DIR="$REPO_ROOT/ci/conan/profiles"
PROFILE_FILE="$PROFILE_DIR/$PROFILE_NAME"

if conan profile list 2>/dev/null | grep -q "^${PROFILE_NAME}$"; then
    echo "[step] Profile ${PROFILE_NAME} already exists"
else
    if [ -f "$PROFILE_FILE" ]; then
        echo "[step] Importing profile from ${PROFILE_FILE}"
        conan profile import "$PROFILE_FILE" 2>/dev/null || true
    else
        echo "[step] Creating default ${PROFILE_NAME} profile..."
        conan profile detect --name "${PROFILE_NAME}" 2>/dev/null || true
    fi
fi

# If profile file exists in repo, use it directly via -pr flag
if [ -f "$PROFILE_FILE" ]; then
    echo "[step] Profile file available at: ${PROFILE_FILE}"
fi

# ── 4. Set conan configuration ──
# Enable revisions (Conan 2.x default, but be explicit)
conan config set general.revisions_enabled=1 2>/dev/null || true

echo "[step] Conan environment ready ✅"
echo "[step]   remote: ${CONAN_REMOTE_NAME}"
echo "[step]   profile: ${PROFILE_NAME}"
echo "[step]   conan: ${CONAN_VERSION}"
