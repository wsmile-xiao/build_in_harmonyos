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
#   - L0: Quality gate (test_package structure + content + MANIFEST checks)
#   - L1: Test execution verification (upstream make check in build() + test_package)
#   - L2: Minimal smoke test (--version / --help)
#   - L4: Static security scan (readelf NX/PIE/RELRO)
#   - L5: Baseline artifact check
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
    for pkg_path in ${=CI_PACKAGES}; do
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
    L0_RESULT="skip"
    L0_DETAIL="not_run"
    L1_RESULT="skip"
    L1_DETAIL="not_run"
    L2_RESULT="skip"
    L2_DETAIL="not_run"
    L4_RESULT="skip"
    L4_DETAIL="not_run"
    L5_RESULT="skip"
    L5_DETAIL="not_run"
    L0_FAILED=false
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

    # ── L0: Quality gate (before conan create) ──
    # 5 层防御: 防止适配组偷懒绕过测试
    echo "[step] L0: Quality gate checks..."
    TEST_PKG_DIR="$pkg_dir/test_package"
    L0_FAILED=false
    L0_ERRORS=""

    # L0a: test_package/ 目录必须存在
    if [ ! -d "$TEST_PKG_DIR" ]; then
        echo "[fail] L0a: test_package/ directory missing"
        L0_FAILED=true
        L0_ERRORS="${L0_ERRORS} no_test_package_dir"
    fi

    # L0b: test_package/conanfile.py 必须存在
    if [ ! -f "$TEST_PKG_DIR/conanfile.py" ]; then
        echo "[fail] L0b: test_package/conanfile.py missing"
        L0_FAILED=true
        L0_ERRORS="${L0_ERRORS} no_test_conanfile"
    fi

    # L0c: test_package/ 下必须有测试源文件 (.c/.cpp/.cc/.cxx/.sh/.py)
    TEST_SOURCES=""
    for ext in c cpp cc cxx sh py; do
        found=$(find "$TEST_PKG_DIR" -maxdepth 2 -name "*.$ext" -not -name "conanfile.py" 2>/dev/null | head -1)
        if [ -n "$found" ]; then
            TEST_SOURCES="$found"
            break
        fi
    done
    if [ -z "$TEST_SOURCES" ]; then
        echo "[fail] L0c: No test source files in test_package/"
        L0_FAILED=true
        L0_ERRORS="${L0_ERRORS} no_test_sources"
    fi

    # L0d: test_package/conanfile.py 必须有 test() 且有 self.run()
    if [ -f "$TEST_PKG_DIR/conanfile.py" ]; then
        if ! grep -q "def test" "$TEST_PKG_DIR/conanfile.py" 2>/dev/null; then
            echo "[fail] L0d: test_package/conanfile.py has no test() method"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} no_test_method"
        elif ! grep -q "self\.run" "$TEST_PKG_DIR/conanfile.py" 2>/dev/null; then
            echo "[fail] L0d: test() method has no self.run() call — likely a stub"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} stub_test_method"
        fi
    fi

    # L0e: test_package/MANIFEST.yml 必须存在 (声明上游测试来源)
    if [ ! -f "$TEST_PKG_DIR/MANIFEST.yml" ]; then
        echo "[fail] L0e: test_package/MANIFEST.yml missing — upstream test declaration required"
        L0_FAILED=true
        L0_ERRORS="${L0_ERRORS} no_manifest"
    fi

    # L0f: conandata.yml patches 格式校验 (Conan 2.x 要求 dict-by-version)
    CONANDATA="$pkg_dir/conandata.yml"
    if [ -f "$CONANDATA" ] && grep -q "^patches:" "$CONANDATA" 2>/dev/null; then
        # 提取 patches 段下的 key (缩进的行, 取第一个 token 去掉引号/冒号)
        while IFS= read -r raw_key; do
            # 去掉前导空格和引号
            key=$(echo "$raw_key" | sed 's/^[[:space:]]*//; s/^["'"'"']//; s/["'"'"']:$//; s/:$//')
            # 跳过子字段、列表项 (- 开头) 和空行
            case "$key" in
                patch_file*|patch_type*|patch_description*|-*|"") continue ;;
            esac
            # 正确格式: key 是版本号 (纯数字+点, 如 1.3.1)
            # 错误格式: key 是文件名 (.patch/.diff 结尾)
            if echo "$key" | grep -qE '\.(patch|diff)$'; then
                echo "[fail] L0f: conandata.yml patches format wrong — key '$key' is a filename, not a version"
                echo "       Conan 2.x uses dict-by-version format:"
                echo "         patches:"
                echo "           \"${pkg_ver}\":"
                echo "             - patch_file: \"patches/$key\""
                L0_FAILED=true
                L0_ERRORS="${L0_ERRORS} bad_patch_format"
                break
            fi
        done < <(sed -n '/^patches:/,/^[a-z]/p' "$CONANDATA" | grep '^[[:space:]]')
    fi

    # L0g: 功能裁剪参数检测 (全量适配要求: 不得关闭可选功能)
    CONANFILE="$pkg_dir/conanfile.py"
    if [ -f "$CONANFILE" ]; then
        # 提取所有 --without-XXX / --disable-XXX 参数
        TRIM_PARAMS=$(grep -oE '\-\-(without|disable)-[a-z0-9_-]+' "$CONANFILE" 2>/dev/null | sort -u || true)
        if [ -n "$TRIM_PARAMS" ]; then
            # 过滤掉允许的例外参数
            ALLOWED="--disable-shared --enable-static --disable-nls --without-man --without-doc --disable-gtk-doc --disable-dependency-tracking"
            while IFS= read -r param; do
                # shellcheck disable=SC2086
                if echo $ALLOWED | grep -qw "$param" 2>/dev/null; then
                    continue
                fi
                echo "[warn] L0g: conanfile.py 含功能裁剪参数 '$param' — 全量适配要求保留所有功能"
                L0_DETAIL="trim_param:$param"
            done <<< "$TRIM_PARAMS"
        fi
    fi

    if [ "$L0_FAILED" = true ]; then
        echo "[fail] ${pkg_name}/${pkg_ver} — L0 quality gate failed:${L0_ERRORS}"
        L0_RESULT="fail"
        L0_DETAIL="gate failed:${L0_ERRORS}"
        echo "L0_RESULT=${L0_RESULT}: ${L0_DETAIL}"
        echo "L1_RESULT=skip: blocked_by_L0"
        echo "L2_RESULT=skip: blocked_by_L0"
        echo "L4_RESULT=skip: blocked_by_L0"
        echo "L5_RESULT=skip: blocked_by_L0"
        FAILED=$((FAILED + 1))
        FAILED_PKGS+=("${pkg_name}/${pkg_ver} (L0 gate:${L0_ERRORS})")
        continue
    fi

    echo "[ok] L0: All quality gate checks passed"
    L0_RESULT="pass"
    L0_DETAIL="all checks passed"

    # ── conan create (with upstream tests in build() + test_package auto-trigger) ──
    # OHOS /tmp is read-only, use build directory instead
    BUILD_LOG="$REPO_ROOT/.ci_logs/conan_build_${pkg_name}_${pkg_ver}.log"
    mkdir -p "$REPO_ROOT/.ci_logs" 2>/dev/null || true
    echo "[step] Running conan create (output logged to $BUILD_LOG)..."

    # CI 必须始终重新构建目标包, 确保运行 make check + test_package
    # --build=missing: 依赖包用缓存
    # --build="${pkg_name}/*": 目标包强制重建
    # timeout: 45 分钟硬超时, 防止交互式测试 (如 bash run-execscript) 卡住 worker
    #   exit code 124 = timeout triggered
    BUILD_TIMEOUT=2700
    set -o pipefail
    timeout --signal=KILL $BUILD_TIMEOUT conan create "$pkg_dir" "${CONAN_CREATE_ARGS[@]}" --build="${pkg_name}/*" 2>&1 | tee "$BUILD_LOG"
    CONAN_RC=$?
    set +o pipefail

    if [ $CONAN_RC -eq 124 ]; then
        echo "[fail] ${pkg_name}/${pkg_ver} — conan create TIMED OUT after ${BUILD_TIMEOUT}s (likely interactive test stuck)"
        echo "L1_RESULT=fail: conan create timed out"
        OVERALL_SUCCESS=false
        continue
    fi

    if [ $CONAN_RC -eq 0 ]; then

        echo "[ok] ${pkg_name}/${pkg_ver} — conan create passed"

        # ── L1: Test execution verification (from conan create log) ──
        # 上一代方案用 conan cache source 获取源码目录跑 make check，
        # 但 Conan 2.x 没有 cache source 子命令，且构建目录已被清理。
        # 新方案: make check 在 conanfile.py 的 build() 方法中执行，
        # test_package 在 conan create 的 test 阶段自动执行，
        # CI 脚本从 conan create 日志中验证测试真实执行。
        echo "[step] L1: Verifying test execution from conan create log..."

        MANIFEST_FILE="$TEST_PKG_DIR/MANIFEST.yml"

        # L1a: conan create 必须进入 test 阶段 (test_package 被执行)
        # 使用 -e 多模式匹配, 避免 \| 在某些 grep 实现上不支持
        if grep -qiE "Launching test_package|Testing the package|Running test\(\)" "$BUILD_LOG" 2>/dev/null; then
            echo "[ok] L1a: test_package was executed by conan create"
            L1_RESULT="pass"
            L1_DETAIL="test_package executed"
        else
            echo "[fail] L1a: No test_package execution trace in log — test was skipped!"
            L1_RESULT="fail"
            L1_DETAIL="test_package not executed"
            L1_FAILED=true
        fi

        # L1b: 检查测试程序真实编译和运行的痕迹
        if [ "$L1_RESULT" != "fail" ]; then
            TEST_COMPILE_LINES=$(grep -cE "(clang|gcc|cc|g\+\+|c\+\+)" "$BUILD_LOG" 2>/dev/null || echo "0")
            TEST_RUN_LINES=$(grep -cE "(\./[a-z]|Running test|PASS|FAIL|ok\b)" "$BUILD_LOG" 2>/dev/null || echo "0")
            if [ "${TEST_COMPILE_LINES:-0}" -gt 0 ] || [ "${TEST_RUN_LINES:-0}" -gt 0 ]; then
                echo "[ok] L1b: Test execution evidence found in log"
            else
                echo "[warn] L1b: No test compile/run evidence — test may be trivial"
            fi
        fi

        # L1c: 如果 conanfile.py 的 build() 方法中有 make check/ctest，
        # 验证日志中有执行痕迹
        if [ "$L1_RESULT" != "fail" ]; then
            if grep -qiE "make.*check|ctest|meson test|pytest" "$BUILD_LOG" 2>/dev/null; then
                echo "[ok] L1c: Upstream official tests (make check/ctest) executed in build phase"
                L1_DETAIL="upstream tests + test_package executed"
            else
                echo "[step] L1c: No upstream make check/ctest in log (may be in test_package only)"
            fi
        fi

        # L1d: 检查 test() 方法不是假运行 (只有 echo/print)
        if [ "$L1_RESULT" != "fail" ]; then
            if grep -qE "self\.run.*(echo|print|true)" "$TEST_PKG_DIR/conanfile.py" 2>/dev/null; then
                echo "[fail] L1d: test() method appears to be a fake test (echo/print/true only)"
                L1_RESULT="fail"
                L1_DETAIL="fake test detected"
                L1_FAILED=true
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
        echo "L0_RESULT=${L0_RESULT}: ${L0_DETAIL}"
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
    "L0": {"result": "${L0_RESULT}", "detail": "${L0_DETAIL}"},
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
