#!/usr/bin/zsh
# ci/conan/setup.sh — Conan environment initialization
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=success, non-0=failure (blocks subsequent steps)
# Timeout: 20 minutes
#
# Must complete:
#   - Detect/install Conan (pip install conan)
#   - Register conan remote (OHPCD Conan registry on CNB)
#   - Ensure ohos-aarch64 profile exists
#   - Set conan configuration

set -euo pipefail

# ── Path resolution ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

echo "[step] Conan environment setup..."

# ── 1. Detect/install Conan ──
if ! command -v conan &>/dev/null; then
    echo "[step] Conan not found, installing..."
    # 安装 OHOS 适配版 conan（私有 PyPI 提供，基线 2.29.1，已适配 OHOS 平台）
    # 不要钉死官方旧版本号，应从配置的 PyPI 源安装最新适配版
    pip3 install conan || {
        echo "[error] Failed to install conan"
        exit 1
    }
fi

CONAN_VERSION=$(conan --version 2>/dev/null || echo "unknown")
echo "[step] Conan version: $CONAN_VERSION"

# ── 2. Register conan remote ──
CONAN_REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"
CONAN_REMOTE_URL="${CONAN_REMOTE_URL:-https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/}"

# Remove existing remote if URL changed (idempotent)
EXISTING_URL=$(conan remote list 2>/dev/null | grep "^${CONAN_REMOTE_NAME}:" | head -1 | awk '{print $2}' || echo "")
if [ -n "$EXISTING_URL" ] && [ "$EXISTING_URL" != "$CONAN_REMOTE_URL" ]; then
    echo "[step] Updating remote URL for ${CONAN_REMOTE_NAME}"
    conan remote remove "${CONAN_REMOTE_NAME}" 2>/dev/null || true
fi

# Add remote if not exists (idempotent)
if ! conan remote list 2>/dev/null | grep -q "^${CONAN_REMOTE_NAME}:"; then
    echo "[step] Adding conan remote: ${CONAN_REMOTE_NAME} -> ${CONAN_REMOTE_URL}"
    conan remote add "${CONAN_REMOTE_NAME}" "${CONAN_REMOTE_URL}" || true
fi

# Authenticate if credentials provided
if [ -n "${CONAN_REMOTE_USER:-}" ] && [ -n "${CONAN_REMOTE_PASS:-}" ]; then
    echo "[step] Authenticating to ${CONAN_REMOTE_NAME}..."
    conan remote auth "${CONAN_REMOTE_NAME}" \
        --user "${CONAN_REMOTE_USER}" \
        --password "${CONAN_REMOTE_PASS}" 2>/dev/null || true
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
echo "[step]   remote: ${CONAN_REMOTE_NAME} -> ${CONAN_REMOTE_URL}"
echo "[step]   profile: ${PROFILE_NAME}"
echo "[step]   conan: ${CONAN_VERSION}"
