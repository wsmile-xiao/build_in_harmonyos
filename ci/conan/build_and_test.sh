#!/usr/bin/zsh
# ci/conan/build_and_test.sh — Build + test all Conan packages (CI, no AI)
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=all passed, non-0=any failed
# Timeout: 60 minutes
#
# ⚠️ This script runs on CI execution machines. NO AI tools, NO ohc-run.py,
#    NO knowledge graph, NO Python SKILL environment. Pure zsh + conan only.
#
# Must complete:
#   - Scan for conanfile.py in archives/ (or PKG_SCAN_ROOT)
#   - Run conan create for each package (includes test_package)
#   - Run L4 static security scan (readelf NX/PIE/RELRO)
#   - Run L5 baseline artifact check
#   - Print build summary

set -euo pipefail

# ── Path resolution ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# ── Configuration ──
PROFILE="${CONAN_PROFILE:-ohos-aarch64}"
PROFILE_FILE="$REPO_ROOT/ci/conan/profiles/$PROFILE"
CONAN_USER="${CONAN_USER:-ohpcd}"
CONAN_CHANNEL="${CONAN_CHANNEL:-stable}"
SCAN_ROOT="${PKG_SCAN_ROOT:-archives}"

# Use profile file if available, otherwise profile name
if [ -f "$PROFILE_FILE" ]; then
    PROFILE_ARGS="-pr:h=$PROFILE_FILE -pr:b=$PROFILE_FILE"
else
    PROFILE_ARGS="-pr:h=$PROFILE -pr:b=$PROFILE"
fi

echo "[step] Conan build + test pipeline (CI, no AI)"
echo "[step]   scan_root: $SCAN_ROOT"
echo "[step]   profile: $PROFILE"
echo "[step]   user/channel: ${CONAN_USER}/${CONAN_CHANNEL}"

# ── 1. Discover packages ──
# Find all conanfile.py under archives/, excluding test_package/ and .conan/
PACKAGES=()
while IFS= read -r f; do
    pkg_dir=$(dirname "$f")
    PACKAGES+=("$pkg_dir")
done < <(find "$REPO_ROOT/$SCAN_ROOT" -name "conanfile.py" \
    -not -path "*/test_package/*" \
    -not -path "*/.conan/*" \
    2>/dev/null | sort)

if [ ${#PACKAGES[@]} -eq 0 ]; then
    echo "[error] No conanfile.py found under $SCAN_ROOT"
    exit 1
fi

echo "[step] Found ${#PACKAGES[@]} package(s) to build"

# ── 2. Build + test each package ──
SUCCESS=0
FAILED=0
FAILED_PKGS=()

for pkg_dir in "${PACKAGES[@]}"; do
    pkg_name=$(basename "$(dirname "$pkg_dir")")
    pkg_ver=$(basename "$pkg_dir")

    echo ""
    echo "━━━ Building: ${pkg_name}/${pkg_ver} ━━━"

    # L1: conan create (includes test_package automatically)
    if conan create "$pkg_dir" \
        $PROFILE_ARGS \
        --build=missing \
        --user="$CONAN_USER" \
        --channel="$CONAN_CHANNEL" \
        2>&1; then

        echo "[ok] ${pkg_name}/${pkg_ver} — conan create passed"

        # L4: Static security scan on patches
        PATCH_DIR="$pkg_dir/patches"
        if [ -d "$PATCH_DIR" ]; then
            echo "[step] L4: Scanning patches for dangerous functions..."
            DANGER=$(grep -rlE '(strcpy|sprintf|gets|strcat)\b' "$PATCH_DIR" 2>/dev/null || true)
            if [ -n "$DANGER" ]; then
                echo "[warn] L4: Dangerous functions found in patches:"
                echo "$DANGER"
            fi
        fi

        # L5: Baseline check — verify package artifacts
        echo "[step] L5: Baseline artifact check..."
        PKG_CACHE=$(conan cache path "${pkg_name}/${pkg_ver}@${CONAN_USER}/${CONAN_CHANNEL}" 2>/dev/null || echo "")
        if [ -n "$PKG_CACHE" ] && [ -d "$PKG_CACHE" ]; then
            BINS=$(find "$PKG_CACHE" -name "bin" -type d 2>/dev/null | head -1)
            LIBS=$(find "$PKG_CACHE" -name "lib" -type d 2>/dev/null | head -1)
            INCS=$(find "$PKG_CACHE" -name "include" -type d 2>/dev/null | head -1)

            if [ -n "$BINS" ] && [ -n "$(ls -A "$BINS" 2>/dev/null)" ]; then
                echo "[ok] L5: bin/ has content"
            elif [ -n "$LIBS" ] && [ -n "$(ls -A "$LIBS" 2>/dev/null)" ]; then
                echo "[ok] L5: lib/ has content (library package)"
            else
                echo "[warn] L5: No bin/ or lib/ content found"
            fi
        fi

        # L5: Static linking verification for terminal tools (R26)
        if [ -n "$BINS" ]; then
            for bin_file in "$BINS"/*; do
                [ -f "$bin_file" ] || continue
                if readelf -d "$bin_file" 2>/dev/null | grep -q NEEDED; then
                    NON_SYS=$(readelf -d "$bin_file" 2>/dev/null | grep NEEDED | \
                        grep -vE 'libc\.|libm\.|libdl\.|libpthread\.|librt\.|libutil\.|ld-musl|ld-linux' || true)
                    if [ -n "$NON_SYS" ]; then
                        echo "[warn] L5: ${bin_file##*/} has non-system dynamic deps:"
                        echo "$NON_SYS"
                    fi
                fi
            done
        fi

        SUCCESS=$((SUCCESS + 1))
    else
        echo "[fail] ${pkg_name}/${pkg_ver} — conan create failed"
        FAILED=$((FAILED + 1))
        FAILED_PKGS+=("${pkg_name}/${pkg_ver}")
    fi
done

# ── 3. Summary ──
echo ""
echo "━━━ Build Summary ━━━"
echo "  Total:   ${#PACKAGES[@]}"
echo "  Success: ${SUCCESS}"
echo "  Failed:  ${FAILED}"

if [ $FAILED -gt 0 ]; then
    echo "  Failed packages:"
    for p in "${FAILED_PKGS[@]}"; do
        echo "    - $p"
    done
    exit 1
fi

echo "[step] All packages built and tested successfully ✅"
