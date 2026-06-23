#!/usr/bin/zsh
# ci/artifacts/sign.sh — GPG signing of build artifacts
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=success, non-0=failure (NON-BLOCKING — warning only)
# Timeout: 10 minutes
#
# Must complete:
#   - Locate build artifacts (conan cache)
#   - GPG sign (generate .sig files)
#   - Generate checksum files (.sha256)
#
# NOTE: This script is non-blocking. If signing fails, the pipeline continues
#       but a warning is emitted.

set -euo pipefail

# ── Configuration ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
CONAN_USER="${CONAN_USER:-ohpcd}"
CONAN_CHANNEL="${CONAN_CHANNEL:-stable}"
GPG_KEY_ID="${GPG_KEY_ID:-}"
SCAN_ROOT="${PKG_SCAN_ROOT:-archives}"

echo "[step] Artifact signing..."

if [ -z "$GPG_KEY_ID" ]; then
    echo "[warn] GPG_KEY_ID not set, skipping signing"
    exit 0
fi

if ! command -v gpg &>/dev/null; then
    echo "[warn] gpg not available, skipping signing"
    exit 0
fi

# ── 1. Discover packages ──
PACKAGES=()
while IFS= read -r f; do
    pkg_dir=$(dirname "$f")
    pkg_name=$(basename "$(dirname "$pkg_dir")")
    pkg_ver=$(basename "$pkg_dir")
    PACKAGES+=("${pkg_name}/${pkg_ver}")
done < <(find "$REPO_ROOT/$SCAN_ROOT" -name "conanfile.py" \
    -not -path "*/test_package/*" \
    -not -path "*/.conan/*" \
    2>/dev/null | sort)

echo "[step] Found ${#PACKAGES[@]} package(s) to sign"

# ── 2. Sign each package ──
SIGNED=0
SKIPPED=0

for ref in "${PACKAGES[@]}"; do
    # Get conan cache path for the package
    PKG_PATH=$(conan cache path "${ref}@${CONAN_USER}/${CONAN_CHANNEL}" 2>/dev/null || echo "")

    if [ -z "$PKG_PATH" ] || [ ! -d "$PKG_PATH" ]; then
        echo "[warn] Cannot locate cache for ${ref}, skipping"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo "[step] Signing artifacts in: ${PKG_PATH}"

    # Sign all ELF binaries and libraries
    find "$PKG_PATH" -type f \( -perm -u+x -o -name "*.so" -o -name "*.a" \) 2>/dev/null | while read -r artifact; do
        # Generate SHA256 checksum
        sha256sum "$artifact" > "${artifact}.sha256" 2>/dev/null || true

        # GPG sign
        gpg --batch --yes --local-user "$GPG_KEY_ID" \
            --output "${artifact}.sig" \
            --detach-sign "$artifact" 2>/dev/null || {
            echo "[warn] Failed to sign: ${artifact##*/}"
        }
    done

    SIGNED=$((SIGNED + 1))
done

echo ""
echo "━━━ Signing Summary ━━━"
echo "  Signed:  ${SIGNED}"
echo "  Skipped: ${SKIPPED}"

if [ $SIGNED -gt 0 ]; then
    echo "[step] Artifact signing completed ✅"
else
    echo "[warn] No artifacts were signed (non-blocking)"
fi

# Always exit 0 — signing is non-blocking per CI_SCRIPT_SPEC
exit 0
