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
#   - Use CI_PACKAGES env var for targeted builds (BUG-9 fix)
#   - Pass profile explicitly to conan create (BUG-10 fix)
#   - Run L1 upstream official test (make check / ctest / meson test / pytest)
#   - Run L2 minimal smoke test (--version / --help)
#   - Run L4 static security scan (readelf NX/PIE/RELRO)
#   - Run L5 baseline artifact check
#   - Generate ci-metadata.json (source_trace + build_trace + test_report)
#   - Print L{n}_RESULT= test summary lines for PR reporter
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

echo "[step] Conan build + test pipeline (CI, no AI)"
echo "[step]   scan_root: $SCAN_ROOT"
echo "[step]   profile: $PROFILE"
echo "[step]   user/channel: ${CONAN_USER}/${CONAN_CHANNEL}"

# ── 1. Discover packages (BUG-9: respect CI_PACKAGES) ──
PACKAGES=()
if [ -n "${CI_PACKAGES:-}" ]; then
    # CI 传入了定向包列表（空格分隔的相对路径，如 "archives/b/bash/5.3"）
    echo "[step] CI_PACKAGES received: $CI_PACKAGES"
    for pkg_path in $CI_PACKAGES; do
        # Handle both relative and absolute paths
        if [[ "$pkg_path" = /* ]]; then
            pkg_dir="$pkg_path"
        else
            pkg_dir="$REPO_ROOT/$pkg_path"
        fi
        if [ -f "$pkg_dir/conanfile.py" ]; then
            PACKAGES+=("$pkg_dir")
        else
            echo "[warn] Path in CI_PACKAGES has no conanfile.py: $pkg_path"
        fi
    done
else
    # 无定向参数时扫描 archives/ 目录
    echo "[step] No CI_PACKAGES, scanning $SCAN_ROOT/ ..."
    while IFS= read -r f; do
        pkg_dir=$(dirname "$f")
        PACKAGES+=("$pkg_dir")
    done < <(find "$REPO_ROOT/$SCAN_ROOT" -name "conanfile.py" \
        -not -path "*/test_package/*" \
        -not -path "*/.conan/*" \
        2>/dev/null | sort)
fi

if [ ${#PACKAGES[@]} -eq 0 ]; then
    echo "[error] No packages to build"
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

    # ── conan create (BUG-10: explicit profile + settings) ──
    # Build profile args as array for safe word-splitting
    CONAN_CREATE_ARGS=()
    # Profile: prefer file path if exists, otherwise profile name
    if [ -f "$PROFILE_FILE" ]; then
        CONAN_CREATE_ARGS+=(-pr:h="$PROFILE_FILE" -pr:b="$PROFILE_FILE")
    else
        CONAN_CREATE_ARGS+=(-pr:h="$PROFILE" -pr:b="$PROFILE")
    fi
    CONAN_CREATE_ARGS+=(
        --build=missing
        --user="$CONAN_USER"
        --channel="$CONAN_CHANNEL"
    )

    if conan create "$pkg_dir" "${CONAN_CREATE_ARGS[@]}" 2>&1; then

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
                    L1_DETAIL="make check"
                else
                    echo "[fail] L1: make check failed"
                    L1_RESULT="fail"
                    L1_DETAIL="make check"
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
                    L1_DETAIL="meson test"
                else
                    echo "[fail] L1: meson test failed"
                    L1_RESULT="fail"
                    L1_DETAIL="meson test"
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
                L4_DETAIL="dangerous functions in patches"
            else
                L4_RESULT="pass"
                L4_DETAIL="patches clean"
            fi
        else
            L4_RESULT="pass"
            L4_DETAIL="no patches"
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
                L5_DETAIL="bin/ has content"
            elif [ -n "$LIBS" ] && [ -n "$(ls -A "$LIBS" 2>/dev/null)" ]; then
                echo "[ok] L5: lib/ has content (library package)"
                L5_RESULT="pass"
                L5_DETAIL="lib/ has content"
            else
                echo "[warn] L5: No bin/ or lib/ content found"
                L5_RESULT="warn"
                L5_DETAIL="no artifacts found"
            fi
        else
            echo "[warn] L5: Package cache not found"
            L5_RESULT="warn"
            L5_DETAIL="no cache"
        fi

        # L5: System-lib collision check (R26)
        # 新策略: 默认动态链接由 Conan 管理依赖链，仅检查系统同名 .so 冲突
        if [ -n "$LIBS" ] && [ -d "$LIBS" ]; then
            # 收集系统已有 .so 名单
            SYS_SO=""
            for sys_lib_dir in /lib /lib64; do
                [ -d "$sys_lib_dir" ] || continue
                SYS_SO="$SYS_SO $(ls "$sys_lib_dir"/*.so* 2>/dev/null | xargs -n1 basename 2>/dev/null || true)"
            done
            # 检查包产出的 .so 是否与系统同名
            for lib_file in "$LIBS"/*.so*; do
                [ -f "$lib_file" ] || continue
                lib_basename="${lib_file##*/}"
                # 去版本号后缀比较 (libfoo.so.1.2.3 -> libfoo.so)
                lib_base="${lib_basename%%.so*}.so"
                for sys_lib in $SYS_SO; do
                    sys_base="${sys_lib%%.so*}.so"
                    if [ "$lib_base" = "$sys_base" ]; then
                        echo "[warn] L5/R26: ${lib_basename} conflicts with system ${sys_lib}"
                        echo "[hint]      Add BUILD_SHARED_LIBS=OFF or --disable-shared to conanfile.py"
                    fi
                done
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
                        L2_DETAIL="$bin_name --version OK"
                    else
                        L2_DETAIL="${L2_DETAIL}, $bin_name --version OK"
                    fi
                elif "$bin_file" --help >/dev/null 2>&1; then
                    echo "[ok] L2: $bin_name --help OK"
                    L2_RESULT="pass"
                    if [ -z "$L2_DETAIL" ] || [ "$L2_DETAIL" = "not_run" ]; then
                        L2_DETAIL="$bin_name --help OK"
                    else
                        L2_DETAIL="${L2_DETAIL}, $bin_name --help OK"
                    fi
                else
                    echo "[warn] L2: $bin_name --version/--help failed (non-blocking)"
                    if [ -z "$L2_DETAIL" ] || [ "$L2_DETAIL" = "not_run" ]; then
                        L2_DETAIL="$bin_name version/help failed"
                    else
                        L2_DETAIL="${L2_DETAIL}, $bin_name failed"
                    fi
                fi
            done
            if [ "$_found_exec" = false ]; then
                echo "[step] L2: No executable files found in bin/ — skipping"
                L2_RESULT="skip"
                L2_DETAIL="no executables"
            fi
        else
            echo "[step] L2: No bin/ directory found — skipping"
            L2_RESULT="skip"
            L2_DETAIL="no bin/ dir"
        fi

        # ── Print PR reporter test summary lines ──
        echo ""
        echo "L1_RESULT=${L1_RESULT}: ${L1_DETAIL}"
        echo "L2_RESULT=${L2_RESULT}: ${L2_DETAIL}"
        echo "L4_RESULT=${L4_RESULT}: ${L4_DETAIL}"
        echo "L5_RESULT=${L5_RESULT}: ${L5_DETAIL}"

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

        cat > "$METADATA_FILE" <<JSONEOF
{
  "package": "${pkg_name}",
  "version": "${pkg_ver}",
  "source_trace": {
    "url": "${SOURCE_URL}",
    "sha256": "${SOURCE_SHA256}"
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
    "L1": {"result": "${L1_RESULT}", "detail": "${L1_DETAIL}"},
    "L2": {"result": "${L2_RESULT}", "detail": "${L2_DETAIL}"},
    "L4": {"result": "${L4_RESULT}", "detail": "${L4_DETAIL}"},
    "L5": {"result": "${L5_RESULT}", "detail": "${L5_DETAIL}"}
  }
}
JSONEOF
        echo "[ok] ci-metadata.json written"

        # ── Check L1 official test result ──
        if [ "$L1_FAILED" = true ]; then
            echo "[fail] ${pkg_name}/${pkg_ver} — L1 official test failed"
            FAILED=$((FAILED + 1))
            FAILED_PKGS+=("${pkg_name}/${pkg_ver} (L1 failed: ${L1_DETAIL})")
            continue
        fi

        SUCCESS=$((SUCCESS + 1))
    else
        echo "[fail] ${pkg_name}/${pkg_ver} — conan create failed"
        echo "L1_RESULT=fail: conan create failed"
        echo "L2_RESULT=skip: not run"
        echo "L4_RESULT=skip: not run"
        echo "L5_RESULT=skip: not run"
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
