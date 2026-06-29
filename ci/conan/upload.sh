#!/usr/bin/zsh
# ci/conan/upload.sh — Upload built packages to Conan registry (CI, no AI)
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=success, non-0=failure
# Timeout: 30 minutes
#
# ⚠️ SECURITY: Only CI_TASK_TYPE=release (post-merge) may call this script.
#    PR check pipeline must NOT upload.
#    Conan registry credentials are pre-deployed by worker app as ~/.conan2/.conan.db
#    (Release machines only). This script does NOT handle credentials.

set -euo pipefail

# ── Security gate ──
if [ "${CI_TASK_TYPE:-}" != "release" ]; then
    echo "[error] Upload is only allowed in release pipeline (CI_TASK_TYPE=release)"
    echo "[error] Current CI_TASK_TYPE=${CI_TASK_TYPE:-unset}"
    exit 1
fi

# ── Configuration ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PROFILE="${CONAN_PROFILE:-ohos-aarch64}"
PROFILE_FILE="$REPO_ROOT/ci/conan/profiles/$PROFILE"
CONAN_USER="${CONAN_USER:-ohpcd}"
CONAN_CHANNEL="${CONAN_CHANNEL:-stable}"
CONAN_REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"

if [ -f "$PROFILE_FILE" ]; then
    PROFILE_ARGS="-pr:h=$PROFILE_FILE -pr:b=$PROFILE_FILE"
else
    PROFILE_ARGS="-pr:h=$PROFILE -pr:b=$PROFILE"
fi

echo "[step] Conan upload pipeline"
echo "[step]   remote: ${CONAN_REMOTE_NAME}"
echo "[step]   user/channel: ${CONAN_USER}/${CONAN_CHANNEL}"

# Conan 认证由 worker app 预部署 (~/.conan2/.conan.db, 仅 Release 机器)
# 本脚本不处理凭证, 直接 conan upload

# ── 1. Discover packages (only from CI_PACKAGES) ──
PACKAGES=()
for pkg_path in ${CI_PACKAGES:-}; do
    # pkg_path 形如 archives/b/bash/5.3
    pkg_ver=$(basename "$pkg_path")
    pkg_name=$(basename "$(dirname "$pkg_path")")
    PACKAGES+=("${pkg_name}/${pkg_ver}@${CONAN_USER}/${CONAN_CHANNEL}")
done

if [ ${#PACKAGES[@]} -eq 0 ]; then
    echo "[error] No packages found to upload (CI_PACKAGES is empty)"
    exit 1
fi

echo "[step] Found ${#PACKAGES[@]} package(s) to upload"

# ── 3. Upload each package ──
SUCCESS=0
FAILED=0

for ref in "${PACKAGES[@]}"; do
    echo ""
    echo "[step] Uploading: ${ref}"
    if conan upload "$ref" -r="${CONAN_REMOTE_NAME}" -c 2>&1; then
        echo "[ok] ${ref} uploaded"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "[fail] ${ref} upload failed"
        FAILED=$((FAILED + 1))
    fi
done

# ── 4. Summary ──
echo ""
echo "━━━ Upload Summary ━━━"
echo "  Total:   ${#PACKAGES[@]}"
echo "  Success: ${SUCCESS}"
echo "  Failed:  ${FAILED}"

if [ $FAILED -gt 0 ]; then
    exit 1
fi

echo "[step] All packages uploaded successfully ✅"
