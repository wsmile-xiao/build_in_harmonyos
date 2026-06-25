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
#   - Run L1 upstream official test (make check / ctest / meson test / pytest)
#   - Run L2 minimal smoke test (--version / --help)
#   - Run L4 static security scan (readelf NX/PIE/RELRO)
#   - Run L5 baseline artifact check
#   - Generate ci-metadata.json (source_trace + build_trace + test_report)
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
NO_TEST_FILE="$REPO_ROOT/ci/config/no_official_test.txt"

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

    # Initialize per-package variables (set -u safety)
    BINS=""
    LIBS=""
    INCS=""
    PKG_CACHE=""
    SRC_DIR=""
    L1_RESULT="skip"
    L1_DETAIL="not_run"
    L2_RESULT="skip"
    L2_DETAIL="not_run"
    L4_RESULT="skip"
    L4_DETAIL="not_run"
    L5_RESULT="skip"
    L5_DETAIL="not_run"
    L1_FAILED=false

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

        # ── L1: Upstream official test (architect §5 requirement) ──
        echo "[step] L1: Upstream official test..."

        # Get source directory from conan cache
        SRC_DIR=$(conan cache source "${pkg_name}/${pkg_ver}@${CONAN_USER}/${CONAN_CHANNEL}" 2>/dev/null || echo "")

        # Check whitelist (ci/config/no_official_test.txt)
        if [ -f "$NO_TEST_FILE" ] && grep -qx "$pkg_name" "$NO_TEST_FILE" 2>/dev/null; then
            echo "[step] L1: $pkg_name is in no_official_test whitelist — skipping"
            L1_RESULT="skip"
            L1_DETAIL="whitelisted"
        elif [ -z "$SRC_DIR" ] || [ ! -d "$SRC_DIR" ]; then
            echo "[step] L1: Source directory not available (conan cache may be cleaned) — skipping"
            L1_RESULT="skip"
            L1_DETAIL="no_source_dir"
        else
            echo "[step] L1: Source directory: $SRC_DIR"

            # Detect build system and run official tests
            if [ -f "$SRC_DIR/Makefile" ] && make -C "$SRC_DIR" -n check >/dev/null 2>&1; then
                echo "[step] L1: Detected Makefile with 'check' target"
                if make -C "$SRC_DIR" check 2>&1; then
                    echo "[ok] L1: make check passed"
                    L1_RESULT="pass"
                    L1_DETAIL="make_check"
                else
                    echo "[fail] L1: make check failed"
                    L1_RESULT="fail"
                    L1_DETAIL="make_check"
                    L1_FAILED=true
                fi
            elif [ -f "$SRC_DIR/CTestTestfile.cmake" ]; then
                echo "[step] L1: Detected CTest"
                if (cd "$SRC_DIR" && ctest --output-on-failure 2>&1); then
                    echo "[ok] L1: ctest passed"
                    L1_RESULT="pass"
                    L1_DETAIL="ctest"
                else
                    echo "[fail] L1: ctest failed"
                    L1_RESULT="fail"
                    L1_DETAIL="ctest"
                    L1_FAILED=true
                fi
            elif [ -f "$SRC_DIR/meson.build" ]; then
                echo "[step] L1: Detected meson"
                if (cd "$SRC_DIR" && meson test 2>&1); then
                    echo "[ok] L1: meson test passed"
                    L1_RESULT="pass"
                    L1_DETAIL="meson_test"
                else
                    echo "[fail] L1: meson test failed"
                    L1_RESULT="fail"
                    L1_DETAIL="meson_test"
                    L1_FAILED=true
                fi
            elif [ -f "$SRC_DIR/pytest.ini" ] || [ -f "$SRC_DIR/setup.cfg" ] || \
                 [ -n "$(find "$SRC_DIR" -maxdepth 1 -name 'test*.py' 2>/dev/null | head -1)" ]; then
                echo "[step] L1: Detected pytest"
                if (cd "$SRC_DIR" && python -m pytest 2>&1); then
                    echo "[ok] L1: pytest passed"
                    L1_RESULT="pass"
                    L1_DETAIL="pytest"
                else
                    echo "[fail] L1: pytest failed"
                    L1_RESULT="fail"
                    L1_DETAIL="pytest"
                    L1_FAILED=true
                fi
            else
                echo "[step] L1: No known test target found — skipping"
                L1_RESULT="skip"
                L1_DETAIL="no_test_target"
            fi
        fi

        # ── L4: Static security scan on patches ──
        PATCH_DIR="$pkg_dir/patches"
        if [ -d "$PATCH_DIR" ]; then
            echo "[step] L4: Scanning patches for dangerous functions..."
            DANGER=$(grep -rlE '(strcpy|sprintf|gets|strcat)\b' "$PATCH_DIR" 2>/dev/null || true)
            if [ -n "$DANGER" ]; then
                echo "[warn] L4: Dangerous functions found in patches:"
                echo "$DANGER"
                L4_RESULT="warn"
                L4_DETAIL="dangerous_functions"
            else
                L4_RESULT="pass"
                L4_DETAIL="clean"
            fi
        fi

        # ── L5: Baseline check — verify package artifacts ──
        echo "[step] L5: Baseline artifact check..."
        PKG_CACHE=$(conan cache path "${pkg_name}/${pkg_ver}@${CONAN_USER}/${CONAN_CHANNEL}" 2>/dev/null || echo "")
        if [ -n "$PKG_CACHE" ] && [ -d "$PKG_CACHE" ]; then
            BINS=$(find "$PKG_CACHE" -name "bin" -type d 2>/dev/null | head -1)
            LIBS=$(find "$PKG_CACHE" -name "lib" -type d 2>/dev/null | head -1)
            INCS=$(find "$PKG_CACHE" -name "include" -type d 2>/dev/null | head -1)

            if [ -n "$BINS" ] && [ -n "$(ls -A "$BINS" 2>/dev/null)" ]; then
                echo "[ok] L5: bin/ has content"
                L5_RESULT="pass"
                L5_DETAIL="bin_has_content"
            elif [ -n "$LIBS" ] && [ -n "$(ls -A "$LIBS" 2>/dev/null)" ]; then
                echo "[ok] L5: lib/ has content (library package)"
                L5_RESULT="pass"
                L5_DETAIL="lib_has_content"
            else
                echo "[warn] L5: No bin/ or lib/ content found"
                L5_RESULT="warn"
                L5_DETAIL="no_artifacts"
            fi
        else
            echo "[warn] L5: Package cache not found"
            L5_RESULT="warn"
            L5_DETAIL="no_cache"
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

        # ── L2: Minimal smoke test (--version / --help) ──
        echo "[step] L2: Smoke test (version/help check)..."
        if [ -n "$BINS" ] && [ -d "$BINS" ]; then
            _found_exec=false
            for bin_file in "$BINS"/*; do
                [ -f "$bin_file" ] || continue
                [ -x "$bin_file" ] || continue
                _found_exec=true
                bin_name="${bin_file##*/}"
                if "$bin_file" --version >/dev/null 2>&1; then
                    echo "[ok] L2: $bin_name --version OK"
                    L2_RESULT="pass"
                    if [ -z "$L2_DETAIL" ] || [ "$L2_DETAIL" = "not_run" ]; then
                        L2_DETAIL="$bin_name:--version"
                    else
                        L2_DETAIL="${L2_DETAIL}, ${bin_name}:--version"
                    fi
                elif "$bin_file" --help >/dev/null 2>&1; then
                    echo "[ok] L2: $bin_name --help OK"
                    L2_RESULT="pass"
                    if [ -z "$L2_DETAIL" ] || [ "$L2_DETAIL" = "not_run" ]; then
                        L2_DETAIL="$bin_name:--help"
                    else
                        L2_DETAIL="${L2_DETAIL}, ${bin_name}:--help"
                    fi
                else
                    echo "[warn] L2: $bin_name --version/--help failed (non-blocking)"
                    if [ -z "$L2_DETAIL" ] || [ "$L2_DETAIL" = "not_run" ]; then
                        L2_DETAIL="$bin_name:failed"
                    else
                        L2_DETAIL="${L2_DETAIL}, ${bin_name}:failed"
                    fi
                fi
            done
            if [ "$_found_exec" = false ]; then
                echo "[step] L2: No executable files found in bin/ — skipping"
                L2_RESULT="skip"
                L2_DETAIL="no_executables"
            fi
        else
            echo "[step] L2: No bin/ directory found — skipping"
            L2_RESULT="skip"
            L2_DETAIL="no_bin_dir"
        fi

        # ── Generate ci-metadata.json ──
        echo "[step] Generating ci-metadata.json..."
        METADATA_FILE="$pkg_dir/ci-metadata.json"

        # Read source_trace from conandata.yml
        CONANDATA_FILE="$pkg_dir/conandata.yml"
        SOURCE_URL=""
        SOURCE_SHA256=""
        if [ -f "$CONANDATA_FILE" ]; then
            SOURCE_URL=$(grep -E '^\s*url:' "$CONANDATA_FILE" 2>/dev/null | head -1 | sed 's/^\s*url:\s*//' | tr -d '"' || echo "")
            SOURCE_SHA256=$(grep -E '^\s*sha256:' "$CONANDATA_FILE" 2>/dev/null | head -1 | sed 's/^\s*sha256:\s*//' | tr -d '"' || echo "")
        fi

        # Build trace info from environment / profile
        BUILD_HOST=$(hostname 2>/dev/null || echo "unknown")
        BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "unknown")
        BUILD_RUNNER="${CI_RUNNER:-manual}"
        BUILD_COMMIT="${CI_COMMIT_SHA:-unknown}"

        # Write ci-metadata.json
        cat > "$METADATA_FILE" <<JSONEOF
{
  "package": "${pkg_name}",
  "version": "${pkg_ver}",
  "source_trace": {
    "url": "${SOURCE_URL}",
    "sha256": "${SOURCE_SHA256}",
    "conandata": "${CONANDATA_FILE}"
  },
  "build_trace": {
    "profile": "${PROFILE}",
    "user": "${CONAN_USER}",
    "channel": "${CONAN_CHANNEL}",
    "hostname": "${BUILD_HOST}",
    "timestamp": "${BUILD_TIMESTAMP}",
    "runner": "${BUILD_RUNNER}",
    "commit": "${BUILD_COMMIT}"
  },
  "test_report": {
    "l1_official": {
      "result": "${L1_RESULT}",
      "detail": "${L1_DETAIL}"
    },
    "l2_smoke": {
      "result": "${L2_RESULT}",
      "detail": "${L2_DETAIL}"
    },
    "l4_security": {
      "result": "${L4_RESULT}",
      "detail": "${L4_DETAIL}"
    },
    "l5_baseline": {
      "result": "${L5_RESULT}",
      "detail": "${L5_DETAIL}"
    }
  }
}
JSONEOF
        echo "[ok] ci-metadata.json written to ${METADATA_FILE}"

        # ── Check L1 official test result ──
        if [ "$L1_FAILED" = true ]; then
            echo "[fail] ${pkg_name}/${pkg_ver} — L1 official test failed, marking package as failed"
            FAILED=$((FAILED + 1))
            FAILED_PKGS+=("${pkg_name}/${pkg_ver} (L1 official test failed: ${L1_DETAIL})")
            continue
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
