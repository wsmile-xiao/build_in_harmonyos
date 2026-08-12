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
CONAN_REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"

echo "[step] Conan upload pipeline"
echo "[step]   remote: ${CONAN_REMOTE_NAME}"
echo "[step]   channel: (no channel — plain name/version)"

# Conan 认证由 worker app 预部署 (~/.conan2/.conan.db, 仅 Release 机器)
# 本脚本不处理凭证, 直接 conan upload

# ── 1. Discover packages (only from CI_PACKAGES) ──
PACKAGES=()
for pkg_path in ${=CI_PACKAGES:-}; do
    # pkg_path 形如 archives/b/bash/5.3
    pkg_ver=$(basename "$pkg_path")
    pkg_name=$(basename "$(dirname "$pkg_path")")
    PACKAGES+=("${pkg_name}/${pkg_ver}")
done

if [ ${#PACKAGES[@]} -eq 0 ]; then
    echo "[error] No packages found to upload (CI_PACKAGES is empty)"
    exit 1
fi

echo "[step] Found ${#PACKAGES[@]} package(s) to upload"

# ── 3. Upload each package (with retry) ──
SUCCESS=0
FAILED=0
MAX_RETRIES=3
RETRY_DELAY=10

for ref in "${PACKAGES[@]}"; do
    echo ""
    echo "[step] Uploading: ${ref}"

    for attempt in $(seq 1 $MAX_RETRIES); do
        # 409 Conflict = 包已存在（之前 upload 成功过），视为幂等成功
        # 注意: set -e 下 var=$(failing_cmd) 会直接退出脚本, 必须用 || 捕获退出码
        exit_code=0
        upload_output=$(conan upload "$ref" -r="${CONAN_REMOTE_NAME}" -c 2>&1) || exit_code=$?

        if [ $exit_code -eq 0 ]; then
            if [ $attempt -gt 1 ]; then
                echo "[ok] ${ref} uploaded (attempt ${attempt}/${MAX_RETRIES})"
            else
                echo "[ok] ${ref} uploaded"
            fi
            SUCCESS=$((SUCCESS + 1))
            break
        fi

        if echo "$upload_output" | grep -qiE "409|already exist|conflict"; then
            echo "[ok] ${ref} already exists in registry (409 idempotent)"
            SUCCESS=$((SUCCESS + 1))
            break
        fi

        if [ $attempt -lt $MAX_RETRIES ]; then
            echo "[warn] ${ref} upload attempt ${attempt}/${MAX_RETRIES} failed (exit=$exit_code), retrying in ${RETRY_DELAY}s..."
            echo "$upload_output" | tail -5
            sleep $RETRY_DELAY
        else
            echo "[fail] ${ref} upload failed after ${MAX_RETRIES} attempts (exit=$exit_code)"
            echo "$upload_output"
            FAILED=$((FAILED + 1))
        fi
    done
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
