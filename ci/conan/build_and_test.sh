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

    # L0f: conandata.yml patches 格式校验 (Conan 2.x 要求 list 格式)
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
                echo "       Use list format (recommended):"
                echo "         patches:"
                echo "           - patch_file: \"patches/$key\""
                echo "             patch_description: \"...\""
                echo "             patch_type: \"portability\""
                L0_FAILED=true
                L0_ERRORS="${L0_ERRORS} bad_patch_format"
                break
            fi
        done < <(sed -n '/^patches:/,/^[a-z]/p' "$CONANDATA" | grep '^[[:space:]]')
    fi

    # L0h: shell 环境变量依赖检测 (R33: 禁止在 self.run() 中裸用 ${CC}/${CFLAGS} 等)
    CONANFILE="$pkg_dir/conanfile.py"
    if [ -f "$CONANFILE" ]; then
        # 检测 self.run() 或 self.run(...) 中的 ${CC}, ${CXX}, ${CFLAGS}, ${LDFLAGS}
        SHELL_ENV_VARS=$(grep -nE 'self\.run\(.*\$\{(CC|CXX|CFLAGS|CXXFLAGS|LDFLAGS|AR|RANLIB)\}' "$CONANFILE" 2>/dev/null || true)
        if [ -n "$SHELL_ENV_VARS" ]; then
            BAD_VAR=$(echo "$SHELL_ENV_VARS" | head -1 | grep -oE '\$\{[A-Z]+\}' | head -1)
            echo "[fail] L0h: conanfile.py 在 self.run() 中依赖未定义 shell 变量 ${BAD_VAR} — 用 self.conf.get() 代替 (R33)"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} shell_env_var_in_run"
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

    # ── GitHub mirror fallback (只处理 github.com, 不影响其他托管平台) ──
    # 将 conandata.yml 中 github.com 的 url 从单值改为列表, 自动加上镜像源 fallback
    # Conan 2.x 的 get() 支持 url 列表, 会逐个尝试直到成功
    if [ -f "$CONANDATA" ] && grep -q 'github\.com' "$CONANDATA" 2>/dev/null; then
        # 只处理精确匹配 https://github.com 的 URL (不影响 gitlab/bitbucket/codeberg 等其他平台)
        if grep -qE 'url:.*https://github\.com/' "$CONANDATA" 2>/dev/null; then
            echo "[step] GitHub mirror fallback: rewriting github.com URLs in conandata.yml..."
            cp "$CONANDATA" "${CONANDATA}.orig" 2>/dev/null

            python3 - "$CONANDATA" <<'PYEOF'
import re, sys

path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

def replace_github_url(match):
    indent = match.group(1)
    quote = match.group(2)
    url = match.group(3)
    mirrors = [
        'https://ghproxy.com/' + url,
        'https://gitclone.com/' + url[len('https://'):],
        'https://moeyy.cn/gh-proxy/' + url,
        url,
    ]
    subindent = indent + '  '
    lines = [indent + 'url:'] + [subindent + '- ' + quote + m + quote for m in mirrors]
    return '\n'.join(lines)

# 只匹配单值 url: "https://github.com/..." (不处理已经是列表的)
pattern = r'^([ \t]*)url:[ \t]*(["\'])(https://github\.com/[^\s"\']+)\2[ \t]*$'
content = re.sub(pattern, replace_github_url, content, flags=re.MULTILINE)

with open(path, 'w') as f:
    f.write(content)
PYEOF

            echo "        [ok] GitHub URLs rewritten with mirror fallback (ghproxy -> gitclone -> moeyy -> direct)"
        fi
    fi

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
    # Disable set -e around conan create — we need to capture the exit code
    # and continue to the next package on failure (BUG: set -e caused premature exit)
    set +e
    timeout --signal=KILL $BUILD_TIMEOUT conan create "$pkg_dir" "${CONAN_CREATE_ARGS[@]}" --build="${pkg_name}/*" 2>&1 | tee "$BUILD_LOG"
    CONAN_RC=${PIPESTATUS[0]:-$?}
    set -e

    if [ $CONAN_RC -eq 124 ]; then
        echo "[fail] ${pkg_name}/${pkg_ver} — conan create TIMED OUT after ${BUILD_TIMEOUT}s"
        echo "[hint] 构建超时 (${BUILD_TIMEOUT} 秒限制)"
        echo "       常见原因: 1) 源码包过大 2) 交互式测试卡住 3) 编译死循环"
        echo "       建议: 1) 检查 test_package 是否有 input() 等交互调用 2) 检查是否需要 -j1 限制并行"
        echo "L0_RESULT=${L0_RESULT}: ${L0_DETAIL}"
        echo "L1_RESULT=fail: conan create timed out"
        echo "L2_RESULT=skip: not run"
        echo "L4_RESULT=skip: not run"
        echo "L5_RESULT=skip: not run"
        FAILED=$((FAILED + 1))
        FAILED_PKGS+=("${pkg_name}/${pkg_ver} (timeout)")
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

        # Check whitelist: if package name is in no_official_test.txt, skip L1
        if [ -f "$NO_TEST_FILE" ] && grep -qx "$pkg_name" "$NO_TEST_FILE" 2>/dev/null; then
            echo "[step] L1: Package '$pkg_name' is in no_official_test.txt whitelist — skipping L1 check"
            L1_RESULT="skip"
            L1_DETAIL="whitelisted (no official test)"
        else

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
        fi  # end of L1 whitelist else

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

        # ── L1e: 破坏性反向验证 (R34: test 必须实质依赖被测包) ──
        # 原理: 将被测包产物替换为损坏版本，重新 conan test (重新编译+链接+运行)
        #   仍 PASS = 假测试 (test 不依赖被测包)
        #   FAIL   = 真测试 (链接/运行确实依赖被测包)
        if [ "$L1_RESULT" != "fail" ] && [ -n "$PKG_CACHE" ] && [ -d "$PKG_CACHE" ]; then
            echo "[step] L1e: Destructive negative test (R34)..."

            _BACKUP_DIR="${TMPDIR:-$HOME/tmp}/l1e_backup_${pkg_name}_$$"
            mkdir -p "$_BACKUP_DIR"

            # 备份并破坏产物 — 静态库 .a 替换为空归档
            find "$PKG_CACHE" -name '*.a' -type f 2>/dev/null | while read -r lib_file; do
                cp "$lib_file" "$_BACKUP_DIR/" 2>/dev/null
                rm -f "$lib_file"
                ar rcs "$lib_file" 2>/dev/null
                echo "        [sabotage] $(basename "$lib_file") → empty archive"
            done

            # 动态库 .so* → 临时移走
            find "$PKG_CACHE" -name '*.so*' -type f 2>/dev/null | while read -r lib_file; do
                cp "$lib_file" "$_BACKUP_DIR/" 2>/dev/null
                rm -f "$lib_file"
                echo "        [sabotage] $(basename "$lib_file") → removed"
            done

            # 可执行文件 bin/* → 替换为 /bin/false
            if [ -n "$BINS" ] && [ -d "$BINS" ]; then
                for bin_file in "$BINS"/*; do
                    [ -f "$bin_file" ] || continue
                    cp "$bin_file" "$_BACKUP_DIR/" 2>/dev/null
                    cp /bin/false "$bin_file" 2>/dev/null || printf '#!/bin/sh\nexit 1\n' > "$bin_file"
                    chmod +x "$bin_file" 2>/dev/null
                    echo "        [sabotage] $(basename "$bin_file") → /bin/false"
                done
            fi

            # 头文件 *.h → 清空
            find "$PKG_CACHE" -name '*.h' -type f 2>/dev/null | while read -r hdr_file; do
                cp "$hdr_file" "$_BACKUP_DIR/" 2>/dev/null
                : > "$hdr_file"
            done
            echo "        [sabotage] headers emptied"

            # 重新 conan test (会重新编译 test_package 源码 + 链接 + 运行)
            conan test "$TEST_PKG_DIR" "${pkg_name}/${pkg_ver}@${CONAN_USER}/${CONAN_CHANNEL}" \
                -pr "$CONAN_PROFILE" --build=missing >/dev/null 2>&1
            _NEG_EXIT=$?

            if [ $_NEG_EXIT -eq 0 ]; then
                echo "[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)"
                echo "        test does not depend on ${pkg_name} — must call its API or execute its binary"
                L1_RESULT="fail"
                L1_DETAIL="negative test: test does not depend on package"
                L1_FAILED=true
            else
                echo "[ok] L1e: Negative test confirmed — test genuinely depends on ${pkg_name}"
            fi

            # 恢复产物
            for _bf in "$_BACKUP_DIR"/*; do
                [ -f "$_bf" ] || continue
                _bn=$(basename "$_bf")
                find "$PKG_CACHE" -name "$_bn" -exec cp "$_bf" {} \; 2>/dev/null
            done
            rm -rf "$_BACKUP_DIR"
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

        # ── 错误诊断提示引擎: 分析 BUILD_LOG 提取可操作的修复建议 ──
        echo ""
        echo "─── 修复建议 ───"
        _HINT_GIVEN=false

        # 1. Go/Rust 工具链缺失 (鸿蒙PC原生环境限制)
        if grep -qiE 'go (compiler|toolchain).*not found|go:.*not found' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] 鸿蒙 PC 原生环境不含 Go 工具链, 暂不支持 Go 包构建"
            echo "       如需支持, 需要在 worker 上安装 Go 工具链 (当前不在 CI 范围内)"
            _HINT_GIVEN=true
        fi
        if grep -qiE 'cargo.*not found|rustc.*not found' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] 鸿蒙 PC 原生环境不含 Rust 工具链, 暂不支持 Rust 包构建"
            _HINT_GIVEN=true
        fi

        # 2. GitHub 网络问题
        if grep -qiE 'github\.com.*(timed.?out|ConnectTimeout|Max retries|Connection.*refused|Connection.*reset)' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] GitHub 源码下载失败 (worker 网络无法直连 github.com)"
            echo "       CI 已自动配置镜像源 fallback (ghproxy/gitclone/moeyy), 如仍失败:"
            echo "       请在 conandata.yml 中将 github.com URL 改为 gitcode.com 镜像 URL"
            _HINT_GIVEN=true
        fi

        # 3. 429 限流
        if grep -qiE '429|rate.?limit|Too Many Requests' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] 源码服务器返回 429 (请求过多/限流)"
            echo "       请稍后重试, 或在 conandata.yml 中使用镜像源 URL"
            _HINT_GIVEN=true
        fi

        # 4. 其他网络问题
        if grep -qiE 'HTTPSConnectionPool|Connection.*reset|download.*failed' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] 源码下载失败, 请检查 conandata.yml 中 URL 是否可访问"
            _HINT_GIVEN=true
        fi

        # 5. 依赖包缺失
        if grep -qiE 'not found in (local cache|remotes)|Unable to find.*remotes|not resolved|Unable to find package' "$BUILD_LOG" 2>/dev/null; then
            _MISSING_DEP=$(grep -oiE "not found.*['\"]([a-z0-9_-]+/[0-9][^'\"]*)['\"]" "$BUILD_LOG" 2>/dev/null | head -1 | grep -oE "[a-z0-9_-]+/[0-9][^'\"]*" || true)
            if [ -n "$_MISSING_DEP" ]; then
                echo "[hint] 依赖包 ${_MISSING_DEP} 未在 conan remote 中找到"
            else
                echo "[hint] 依赖包未构建, 请先提交依赖包的 PR 并等待 CI 通过"
            fi
            echo "       请检查 conanfile.py 的 requirements() 是否正确声明了所有依赖"
            _HINT_GIVEN=true
        fi

        # 6. Python 语法错误
        if grep -qiE 'SyntaxError|unterminated string|unexpected EOF' "$BUILD_LOG" 2>/dev/null; then
            _SYN_ERR=$(grep -E 'SyntaxError|unterminated|unexpected' "$BUILD_LOG" | tail -1)
            echo "[hint] conanfile.py Python 语法错误:"
            echo "       $_SYN_ERR"
            echo "       请检查引号/括号是否闭合, 缩进是否正确"
            _HINT_GIVEN=true
        fi

        # 7. sha256 占位符
        if grep -qiE 'REPLACE_WITH|sha256.*placeholder|Provided hash.*REPLACE' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] conandata.yml 中 sha256 仍是占位符"
            echo "       请下载源码包后计算实际 sha256 值: sha256sum xxx.tar.gz"
            echo "       并替换 conandata.yml 中的 REPLACE_WITH 实际值"
            _HINT_GIVEN=true
        fi

        # 8. patch 文件错误
        if grep -qiE 'patch.*(does not exist|Failed to apply|Failed to parse)|source.*file does not exist' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] patch 文件路径或格式错误"
            echo "       请检查 conandata.yml 中 patch_file 路径与 patches/ 目录下文件是否一致"
            _HINT_GIVEN=true
        fi

        # 9. conanfile.py 加载/导入错误
        if grep -qiE 'Unable to load conanfile|Error loading conanfile|import.*failed' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] conanfile.py 加载失败"
            echo "       请检查 import 语句是否正确, Conan 2.x 的 import 路径是否匹配"
            _HINT_GIVEN=true
        fi

        # 10. Conan API 调用错误
        if grep -qiE 'takes 1 positional argument|env argument.*should be a list|AssertionError.*env' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] Conan API 调用方式有误 (Conan 2.x 与 1.x API 差异)"
            echo "       请参考 SKILL.md 中的模板和 Conan 2.x 官方文档"
            _HINT_GIVEN=true
        fi

        # 11. 编译错误 — 链接失败
        if grep -qiE 'undefined reference|cannot find -l|ld returned' "$BUILD_LOG" 2>/dev/null; then
            _UNDEF_SYM=$(grep -oE "undefined reference to .[a-z_][a-z0-9_]*" "$BUILD_LOG" | head -1 || true)
            echo "[hint] 链接错误: ${_UNDEF_SYM:-找不到符号或库}"
            echo "       请在 conanfile.py 的 requirements() 中声明提供该符号的依赖包"
            _HINT_GIVEN=true
        fi

        # 12. 编译错误 — 头文件缺失
        if grep -qiE 'fatal error.*\.h.*No such file|Cannot find.*\.h' "$BUILD_LOG" 2>/dev/null; then
            _MISSING_HDR=$(grep -oE '[a-z_][a-z0-9_/]*\.h' "$BUILD_LOG" | tail -1 || true)
            echo "[hint] 缺少头文件: ${_MISSING_HDR}"
            echo "       请在 conanfile.py 的 requirements() 中声明提供该头文件的依赖包"
            _HINT_GIVEN=true
        fi

        # 13. configure 失败
        if grep -qiE 'configure.*[Ee]rror|configure.*failed|config\.status.*error' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] configure 脚本执行失败"
            echo "       请检查: 1) 系统依赖是否满足 2) configure 参数是否正确"
            echo "       可参考 SKILL.md 中 Autotools 模板的 configure 选项配置"
            _HINT_GIVEN=true
        fi

        # 14. make 编译错误 (最后的兜底)
        if grep -qiE '(make|cc|clang|gcc).*[Ee]rror [0-9]|^.*error:' "$BUILD_LOG" 2>/dev/null; then
            _MAKE_ERR=$(grep -E '[Ee]rror' "$BUILD_LOG" | grep -v '^\[' | tail -1 | head -c 200 || true)
            echo "[hint] 编译失败:"
            echo "       ${_MAKE_ERR}"
            echo "       请检查源码在鸿蒙 PC (clang/ohos) 上的兼容性"
            echo "       常见原因: 1) 编译器差异(gcc→clang) 2) 平台宏未覆盖 3) 缺少系统头文件"
            _HINT_GIVEN=true
        fi

        # 15. OHOS NDK/SDK 缺失
        if grep -qiE 'OHOS NDK.*not found|clang.*not found|OHOS_NDK_ROOT' "$BUILD_LOG" 2>/dev/null; then
            echo "[hint] OHOS NDK/SDK 缺失, worker 环境异常"
            echo "       请联系 CI 管理员检查 worker 上的 OHOS SDK 安装"
            _HINT_GIVEN=true
        fi

        # 兜底: 无法分类
        if [ "$_HINT_GIVEN" = false ]; then
            echo "[hint] 未能自动诊断失败原因, 请查看上方完整构建日志"
            echo "       常见排查: 1) conanfile.py 语法 2) conandata.yml URL/sha256 3) 系统依赖"
        fi
        echo "─── end 修复建议 ───"
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
