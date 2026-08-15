#!/usr/bin/zsh
# ci/conan/build_and_test.sh — Build + test all Conan packages (CI, no AI)
#
# Contract: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos_ci/blob/main/docs/CI_SCRIPT_SPEC.md
# Exit code: 0=all passed, non-0=any failed
# Timeout: 45 minutes by default; reviewed package overrides are capped at 180 minutes
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
# 忽略 SIGPIPE：防止 grep|tail/head 等管道中读端提前关闭导致写端 exit 141
# （zsh + pipefail 下 SIGPIPE 会令整个脚本崩溃）
trap '' PIPE

# ── Path resolution ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="${CI_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# ── Configuration ──
PROFILE="${CONAN_PROFILE:-ohos-aarch64}"
PROFILE_FILE="$REPO_ROOT/ci/conan/profiles/$PROFILE"
CONAN_REMOTE_NAME="${CONAN_REMOTE_NAME:-ohpcd}"
SCAN_ROOT="${PKG_SCAN_ROOT:-archives}"
NO_TEST_FILE="$REPO_ROOT/ci/config/no_official_test.txt"
BUILD_TIMEOUT_CONFIG="$REPO_ROOT/ci/config/build_timeouts.txt"
DEFAULT_BUILD_TIMEOUT=3600
MAX_BUILD_TIMEOUT=14400
TIMEOUT_CLOCK_TOLERANCE=1

validate_build_timeout_config() {
    awk -v min="$DEFAULT_BUILD_TIMEOUT" -v max="$MAX_BUILD_TIMEOUT" '
        function fail(message) {
            print "[fail] Invalid build timeout config at line " NR ": " message > "/dev/stderr"
            invalid = 1
            exit 1
        }

        /^[[:space:]]*(#.*)?$/ { next }
        NF != 2 { fail("expected: name/version seconds") }
        $1 !~ /^[A-Za-z0-9_.+-]+\/[A-Za-z0-9_.+-]+$/ { fail("invalid package reference: " $1) }
        $2 !~ /^[0-9]+$/ { fail("timeout must be an integer: " $2) }
        seen[$1]++ { fail("duplicate package reference: " $1) }
        ($2 + 0) < min || ($2 + 0) > max {
            fail("timeout for " $1 " must be between " min " and " max " seconds")
        }

        END { exit invalid ? 1 : 0 }
    ' "$BUILD_TIMEOUT_CONFIG"
}

build_timeout_for() {
    local package_ref="$1"
    local configured

    configured=$(awk -v ref="$package_ref" '$1 == ref { print $2; exit }' "$BUILD_TIMEOUT_CONFIG")
    echo "${configured:-$DEFAULT_BUILD_TIMEOUT}"
}

is_build_timeout_result() {
    local result="$1"
    local elapsed="$2"
    local limit="$3"

    { [ "$result" -eq 124 ] || [ "$result" -eq 137 ]; } && \
        [ $((elapsed + TIMEOUT_CLOCK_TOLERANCE)) -ge "$limit" ]
}

echo "[step] Conan build + test pipeline (CI, no AI)"
echo "[step]   scan_root: $SCAN_ROOT"
echo "[step]   profile: $PROFILE"
echo "[step]   channel: (no channel — plain name/version)"

if [ ! -f "$BUILD_TIMEOUT_CONFIG" ]; then
    echo "[fail] Missing build timeout config: $BUILD_TIMEOUT_CONFIG"
    exit 1
fi
echo "[step] Validating package build timeout overrides..."
validate_build_timeout_config

# ── 0. Knowledge graph integrity gate (G0) ──
# 全局前置检查：知识库文件路径规范，在任何包构建之前执行
# 贡献者只能提交草稿到 knowledge/drafts/，正式条目由主编审核后入库
G0_ERRORS=0
GRAPH_DIR_G0="${REPO_ROOT}/knowledge/graph"

if [ -d "${GRAPH_DIR_G0}" ]; then
    echo "[step] G0: Knowledge graph integrity check..."

    # G0a: knowledge/graph/draft/ 目录不应存在
    if [ -d "${GRAPH_DIR_G0}/draft" ]; then
        G0_DRAFT_COUNT=$(ls -1 "${GRAPH_DIR_G0}/draft"/*.kv 2>/dev/null | wc -l)
        if [ "${G0_DRAFT_COUNT}" -gt 0 ]; then
            echo "[fail] G0a: knowledge/graph/draft/ 目录存在 ${G0_DRAFT_COUNT} 个草稿 — 草稿只能放在 knowledge/drafts/"
            G0_ERRORS=$((G0_ERRORS + 1))
        fi
    fi

    # G0b: knowledge/graph/ 下不应有非标准命名的 .kv 文件
    #     （只允许 E###.kv + _template.kv + principles.kv）
    G0_BAD_KV=$(ls -1 "${GRAPH_DIR_G0}"/*.kv 2>/dev/null | grep -vE '/E[0-9][0-9][0-9]\.kv$|/_template\.kv$|/principles\.kv$' || true)
    if [ -n "$G0_BAD_KV" ]; then
        G0_BAD_COUNT=$(echo "$G0_BAD_KV" | wc -l)
        echo "[fail] G0b: knowledge/graph/ 下有 ${G0_BAD_COUNT} 个非标准命名的 .kv 文件（仅允许 E###.kv）:"
        echo "$G0_BAD_KV" | head -5 | sed "s|^|       |"
        G0_ERRORS=$((G0_ERRORS + 1))
    fi

    # G0c: knowledge/graph/ 下的 .kv 文件不应含 draft:true 或 contributor_id 字段
    G0_FIELD_LEAK=$(grep -rl '^draft:[[:space:]]*true\|^contributor_id:' "${GRAPH_DIR_G0}"/E*.kv 2>/dev/null || true)
    if [ -n "$G0_FIELD_LEAK" ]; then
        echo "[fail] G0c: 正式条目含草稿字段 (draft:true / contributor_id):"
        echo "$G0_FIELD_LEAK" | head -5 | sed "s|^|       |"
        G0_ERRORS=$((G0_ERRORS + 1))
    fi

    # G0d: index.tsv 行数必须与标准 .kv 文件数一致
    G0_KV_COUNT=$(ls -1 "${GRAPH_DIR_G0}"/E[0-9][0-9][0-9].kv 2>/dev/null | wc -l)
    if [ -f "${GRAPH_DIR_G0}/index.tsv" ]; then
        G0_IDX_COUNT=$(grep -c '^E[0-9]' "${GRAPH_DIR_G0}/index.tsv" 2>/dev/null || echo 0)
        if [ "${G0_IDX_COUNT}" -ne "${G0_KV_COUNT}" ]; then
            echo "[fail] G0d: index.tsv 行数(${G0_IDX_COUNT}) vs .kv 文件数(${G0_KV_COUNT}) 不匹配"
            G0_ERRORS=$((G0_ERRORS + 1))
        fi
    fi

    if [ "$G0_ERRORS" -gt 0 ]; then
        echo ""
        echo "[fail] G0: Knowledge graph integrity check failed (${G0_ERRORS} errors)"
        echo "       知识库草稿只能提交到 knowledge/drafts/，正式条目由主编审核入库"
        echo "G0_RESULT=fail: ${G0_ERRORS} errors"
        echo "L0_RESULT=skip: blocked_by_G0"
        echo "L1_RESULT=skip: blocked_by_G0"
        echo "L2_RESULT=skip: blocked_by_G0"
        echo "L4_RESULT=skip: blocked_by_G0"
        echo "L5_RESULT=skip: blocked_by_G0"
        exit 1
    else
        echo "        [ok] G0: Knowledge graph integrity check passed (${G0_KV_COUNT} entries)"
        echo "G0_RESULT=pass"
    fi
fi

# G0e: 仓库根目录文件白名单检查
# 贡献者不应在根目录放置临时文件（ISSUE/PR草稿/笔记等）
G0_ROOT_ALLOWED=".gitignore|CONTRIBUTING.md|KNOW_YOUR_WHY.md|LICENSE|README.md|SKILL.md|SUMMARY.md"
echo "[step] G0e: Root directory whitelist check..."
G0_ROOT_VIOLATIONS=""
for f in $(git ls-files --full-name | grep -v '/'); do
    if ! echo "$G0_ROOT_ALLOWED" | grep -qFx "$f" 2>/dev/null; then
        case "$f" in
            .gitignore|CONTRIBUTING.md|KNOW_YOUR_WHY.md|LICENSE|README.md|SKILL.md|SUMMARY.md)
                ;;
            *)
                G0_ROOT_VIOLATIONS="${G0_ROOT_VIOLATIONS} ${f}"
                ;;
        esac
    fi
done
if [ -n "$G0_ROOT_VIOLATIONS" ]; then
    echo "[fail] G0e: 根目录存在非白名单文件（仅允许 ${G0_ROOT_ALLOWED}）:"
    for f in $G0_ROOT_VIOLATIONS; do
        echo "       ${f}"
    done
    echo "[hint]  PR 草稿/笔记/Issue 描述请放在对应包的 archives/ 目录或 PR 描述中"
    echo "G0_RESULT=fail: root whitelist violation"
    echo "L0_RESULT=skip: blocked_by_G0"
    echo "L1_RESULT=skip: blocked_by_G0"
    echo "L2_RESULT=skip: blocked_by_G0"
    echo "L4_RESULT=skip: blocked_by_G0"
    echo "L5_RESULT=skip: blocked_by_G0"
    exit 1
else
    echo "        [ok] G0e: Root directory whitelist passed"
fi

# ── 1. Discover packages (BUG-9: respect CI_PACKAGES) ──
# CI_PACKAGES 可通过环境变量或位置参数传入（位置参数在部分鸿蒙 worker
# 上比 env 更可靠，buildbot command= 也用位置参数传递）
if [ -z "${CI_PACKAGES:-}" ] && [ $# -gt 0 ]; then
    CI_PACKAGES="$*"
fi
PACKAGES=()
MISSING_CONANFILE=()

# The PR orchestrator always defines CI_PACKAGES. An explicitly empty value
# means that the PR changed no Conan archive package. Keep the unset,
# release, and explicit CI_BUILD_ALL cases for full-repository validation.
if (( ${+CI_PACKAGES} )) \
    && [ -z "$CI_PACKAGES" ] \
    && [ "${CI_TASK_TYPE:-}" != "release" ] \
    && [ "${CI_BUILD_ALL:-0}" != "1" ]; then
    echo "[step] CI_PACKAGES is explicitly empty; no Conan packages changed"
    echo "L0_RESULT=pass: no applicable Conan packages"
    echo "L1_RESULT=pass: no applicable Conan packages"
    echo "L2_RESULT=skip: no applicable Conan packages"
    echo "L4_RESULT=skip: no applicable Conan packages"
    echo "L5_RESULT=skip: no applicable Conan packages"
    echo ""
    echo "━━━ Build Summary ━━━"
    echo "  Total:   0"
    echo "  Success: 0"
    echo "  Failed:  0"
    echo "  Pass rate: N/A (0 packages)"
    echo "[step] No Conan packages to build"
    exit 0
fi

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
            MISSING_CONANFILE+=("$pkg_path")
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
    echo ""
    echo "─── 修复建议 ───"
    if [ -n "${CI_PACKAGES:-}" ] && [ ${#MISSING_CONANFILE[@]} -gt 0 ]; then
        # CI_PACKAGES 指定的路径都没找到 conanfile.py
        echo "[hint] CI_PACKAGES 指定的路径中没有 conanfile.py"
        echo "       CI_PACKAGES = $CI_PACKAGES"
        echo ""
        echo "       这通常意味着 PR 只改了 conandata.yml（源码下载元数据）"
        echo "       但没有包含 conanfile.py（构建脚本）"
        echo ""
        echo "       请在以下目录创建 conanfile.py（参考 templates/ 目录模板）:"
        for missing_path in "${MISSING_CONANFILE[@]}"; do
            echo "         - $missing_path/conanfile.py"
        done
    else
        echo "[hint] 在 $SCAN_ROOT/ 下没有找到任何 conanfile.py"
        echo "       请确保 archives/字母/包名/版本/conanfile.py 文件存在"
    fi
    echo "─── end 修复建议 ───"
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

    # Unset CONAN_USER/CONAN_CHANNEL to prevent channel injection into dependency resolution
    unset CONAN_USER CONAN_CHANNEL
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
        found=$(find "$TEST_PKG_DIR" -maxdepth 2 -name "*.$ext" -not -name "conanfile.py" -print -quit 2>/dev/null)
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
            BAD_VAR=$(awk 'NR==1{line=$0} END{if(match(line,/\$\{[A-Z]+\}/)) print substr(line,RSTART,RLENGTH)}' <<< "$SHELL_ENV_VARS")
            echo "[fail] L0h: conanfile.py 在 self.run() 中依赖未定义 shell 变量 ${BAD_VAR} — 用 self.conf.get() 代替 (R33)"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} shell_env_var_in_run"
        fi
    fi

    # L0g: 禁止 conanfile.py 中硬编码 remote 名称 (remote 属于环境配置)
    if [ -f "$CONANFILE" ]; then
        REMOTE_HARDCODE=$(grep -nE 'conan\s+(install|download|create|upload|export).*\s-r[= ]' "$CONANFILE" 2>/dev/null || true)
        if [ -n "$REMOTE_HARDCODE" ]; then
            echo "[fail] L0g: conanfile.py 禁止硬编码 remote 名称 (-r=), remote 属于 CI 环境配置"
            echo "       ${REMOTE_HARDCODE%%$'\n'*}"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} hardcoded_remote"
        fi
    fi

    # L0i: 依赖发布检查 (R36: 依赖必须先发布到制品仓)
    # 从 conanfile.py 中提取 requires/requirements 声明的依赖, 验证是否已发布
    # R36: 依赖必须先发布到制品仓
    if [ -f "$CONANFILE" ]; then
        # 提取所有依赖引用（使用 AST 解析，避免误匹配 docstring 中的文本）
        DEP_REFS=$(python3 - "$CONANFILE" "${pkg_name:-}" "${pkg_ver:-}" 2>/dev/null <<'PYEOF'
import ast, sys
src = open(sys.argv[1]).read()
self_name = sys.argv[2] if len(sys.argv) > 2 else ""
self_ver = sys.argv[3] if len(sys.argv) > 3 else ""
self_ref = f"{self_name}/{self_ver}" if self_name and self_ver else ""
refs = set()
tree = ast.parse(src)
for node in ast.walk(tree):
    # 匹配 requires("dep/version") 和 tool_requires("dep/version") 调用
    if isinstance(node, ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id
        if func_name in ("requires", "tool_requires", "build_requires"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    ref = arg.value.strip()
                    if "/" not in ref:
                        continue
                    ref = ref.split("@")[0]
                    # 排除包自身引用
                    if self_ref and ref == self_ref:
                        continue
                    refs.add(ref)
for r in sorted(refs):
    print(r)
PYEOF
)
        if [ -n "$DEP_REFS" ]; then
            echo "[step] L0i: Checking dependency availability in registry (R36)..."
            UNPUBLISHED_DEPS=""
            while IFS= read -r dep_ref; do
                [ -z "$dep_ref" ] && continue
                # R35: 用 conan download 验证 (禁止用 conan list 判断)
                if conan download "$dep_ref" -r="${CONAN_REMOTE_NAME}" --only-recipe >/dev/null 2>&1; then
                    echo "        [ok] dependency in registry: ${dep_ref}"
                else
                    UNPUBLISHED_DEPS="${UNPUBLISHED_DEPS} ${dep_ref}"
                    echo "        [warn] dependency NOT in registry: ${dep_ref}"
                fi
            done <<< "$DEP_REFS"

            if [ -n "$UNPUBLISHED_DEPS" ]; then
                if [ "${CI_TASK_TYPE:-}" = "release" ]; then
                    echo "[fail] L0i: Dependencies not published to registry (R36):${UNPUBLISHED_DEPS}"
                    echo "       These packages must be published FIRST (via release pipeline)."
                    echo "[hint] 依赖未发布到制品仓 (R36)。请先发布以下依赖包:"
                    for d in ${=UNPUBLISHED_DEPS}; do  # zsh: ${=} forces word-splitting
                        echo "         - $d"
                    done
                    L0_FAILED=true
                    L0_ERRORS="${L0_ERRORS} unpublished_deps"
                else
                    echo "[warn] L0i: Dependencies not yet published (R36):${UNPUBLISHED_DEPS}"
                    echo "       Release 时将被拦截。请先适配并发布以上依赖包。"
                    echo "       当前 PR 构建将使用 --build=missing 从源码编译依赖（可能较慢）"
                    echo "[hint] 运行 'bash ci/scripts/preflight_check.sh ${pkg_name}/${pkg_ver}' 检查依赖状态"
                fi
            fi
        fi
    fi

    # ── L0i-1: Export local recipes for unpublished dependencies (R36 fallback) ──
    # When dependencies are not yet published to the registry, export their
    # recipes from the local archives/ directory so --build=missing can compile
    # them from source during conan create.
    if [ -n "${UNPUBLISHED_DEPS:-}" ]; then
        for dep_ref in ${=UNPUBLISHED_DEPS}; do  # zsh: ${=} forces word-splitting (BUG-9 style)
            dep_name=$(echo "$dep_ref" | cut -d'/' -f1)
            dep_ver=$(echo "$dep_ref" | cut -d'/' -f2)
            local_recipe=$(find "$REPO_ROOT/archives" -path "*/${dep_name}/${dep_ver}/conanfile.py" -not -path "*/test_package/*" -print -quit 2>/dev/null)
            if [ -n "$local_recipe" ]; then
                echo "[step] Exporting local recipe for missing dependency: $dep_ref"
                conan export "$(dirname "$local_recipe")" 2>/dev/null && \
                    echo "        [ok] local recipe exported: $dep_ref" || \
                    echo "        [warn] failed to export local recipe: $dep_ref"
            else
                echo "        [warn] no local recipe found for: $dep_ref"
            fi
        done
    fi

    # ── L0j: 版本号占用检查 (R37) ──
    # cnb.cool 制品仓不支持同版本多 revision 并存
    # 如果制品仓中已有该版本, 且 conanfile.py/conandata.yml 有修改 → 必须递增版本号
    echo "[step] L0j: Checking version collision with registry (R37)..."
    if conan download "${pkg_name}/${pkg_ver}" -r="${CONAN_REMOTE_NAME}" --only-recipe >/dev/null 2>&1; then
        # 制品仓中已存在该版本, 比较 recipe 内容
        REMOTE_CACHE_DIR=$(conan cache path "${pkg_name}/${pkg_ver}" 2>/dev/null || echo "")
        if [ -n "$REMOTE_CACHE_DIR" ]; then
            RECIPE_CHANGED=false
            # 比较 conanfile.py
            if [ -f "$REMOTE_CACHE_DIR/conanfile.py" ]; then
                if ! diff -q "$CONANFILE" "$REMOTE_CACHE_DIR/conanfile.py" >/dev/null 2>&1; then
                    RECIPE_CHANGED=true
                fi
            fi
            # 比较 conandata.yml (如果存在)
            if [ -f "$CONANDATA" ] || [ -f "$REMOTE_CACHE_DIR/conandata.yml" ]; then
                if ! diff -q "$CONANDATA" "$REMOTE_CACHE_DIR/conandata.yml" >/dev/null 2>&1; then
                    RECIPE_CHANGED=true
                fi
            fi

            if [ "$RECIPE_CHANGED" = true ]; then
                echo "[fail] L0j: ${pkg_name}/${pkg_ver} already published with different recipe (R37)"
                echo "       制品仓中已存在 ${pkg_name}/${pkg_ver}, 且本次修改了 conanfile.py 或 conandata.yml"
                echo "       cnb.cool 制品仓不支持同版本多 revision 并存 (409 Conflict)"
                echo "[hint] 适配修复必须递增版本号后缀:"
                echo "         ${pkg_name}/${pkg_ver} → ${pkg_name}/${pkg_ver}.1"
                echo "       并更新 archives/ 目录和所有下游引用"
                L0_FAILED=true
                L0_ERRORS="${L0_ERRORS} version_not_incremented"
            else
                echo "        [ok] recipe unchanged (same content as registry)"
            fi
        fi
    else
        echo "        [ok] version not in registry yet (first publish)"
    fi

    # ── L0k: 命令行工具声明检查 (R38) ──
    # 如果 conanfile.py 构建产物包含可执行文件 (bin/), 必须有 commands.json (软件级)
    # 仅当 conanfile 位于 archives/<字母>/<包名>/<版本>/ 标准路径下时强制检查
    # （非 archives 路径的构建场景跳过，避免误伤）
    echo "[step] L0k: Checking commands.json for CLI tools (R38)..."
    CONANFILE_DIR="$(dirname "$CONANFILE")"
    # commands.json 在软件级别目录 (上两级: {version}/ → {name}/)
    PKG_SOFTWARE_DIR="$(dirname "$CONANFILE_DIR")"
    COMMANDS_JSON="${PKG_SOFTWARE_DIR}/commands.json"
    case "$CONANFILE" in
        */archives/*) L0K_APPLICABLE=true ;;
        *)            L0K_APPLICABLE=false ;;
    esac
    if [ "$L0K_APPLICABLE" = "false" ]; then
        echo "        [info] L0k: skipped (conanfile not under archives/, path: $CONANFILE)"
    else
    # 检查 conanfile.py 是否构建可执行文件 (package_info 中有 bindirs 或 build install bin/)
    HAS_BINDIRS=$(grep -c 'bindirs\|cpp_info\.bindirs\|bindirs\s*=' "$CONANFILE" 2>/dev/null || true)
    # 收紧安装目标检测: 只认 CMake RUNTIME DESTINATION bin 与 self.copy(dst="bin")
    # （旧正则 install.*bin 会误匹配 set(INSTALL_BINDIR)/注释等，提升 fail 后必须防误伤）
    HAS_BIN_INSTALL=$(grep -cE 'RUNTIME[[:space:]]+DESTINATION[[:space:]]+bin\b|dst\s*=\s*["'"'"']bin["'"'"']' "$CONANFILE" 2>/dev/null || true)
    HAS_EXECUTABLE=$(grep -c 'package_type.*=.*"application"\|package_type.*=.*'\''application' "$CONANFILE" 2>/dev/null || true)
    HAS_BINDIRS=${HAS_BINDIRS:-0}
    HAS_BIN_INSTALL=${HAS_BIN_INSTALL:-0}
    HAS_EXECUTABLE=${HAS_EXECUTABLE:-0}

    if [ "$HAS_BINDIRS" -gt 0 ] || [ "$HAS_BIN_INSTALL" -gt 0 ] || [ "$HAS_EXECUTABLE" -gt 0 ]; then
        # 这是一个命令行工具, 检查 commands.json 是否存在
        if [ -f "$COMMANDS_JSON" ]; then
            # 验证 JSON 格式和 type 字段
            if command -v python3 >/dev/null 2>&1; then
                JSON_VALID=$(python3 -c "
import json, sys
try:
    d = json.load(open('$COMMANDS_JSON'))
    if d.get('type') != 'tool':
        print('BAD_TYPE')
    elif '$pkg_name' not in d.get('name', ''):
        print('BAD_NAME')
    elif '$pkg_ver' not in d.get('versions', {}):
        print('BAD_VERSION')
    else:
        print('OK')
except Exception:
    print('INVALID_JSON')
" 2>/dev/null)
                case "$JSON_VALID" in
                    OK)
                        echo "        [ok] commands.json valid (type=tool)"
                        ;;
                    INVALID_JSON)
                        echo "[fail] L0k: commands.json exists but is invalid JSON (R38)"
                        echo "[hint] 参考 templates/commands.json.template 格式"
                        L0_FAILED=true
                        L0_ERRORS="${L0_ERRORS} commands_json_r38"
                        ;;
                    BAD_TYPE)
                        echo "[fail] L0k: commands.json type should be \"tool\" (R38)"
                        L0_FAILED=true
                        L0_ERRORS="${L0_ERRORS} commands_json_r38"
                        ;;
                    BAD_NAME)
                        echo "[fail] L0k: commands.json name mismatch (expected: $pkg_name) (R38)"
                        L0_FAILED=true
                        L0_ERRORS="${L0_ERRORS} commands_json_r38"
                        ;;
                    BAD_VERSION)
                        echo "[fail] L0k: commands.json missing version $pkg_ver (R38)"
                        echo "[hint] 递增版本号时须同步在 commands.json 的 versions 中补 $pkg_ver"
                        L0_FAILED=true
                        L0_ERRORS="${L0_ERRORS} commands_json_r38"
                        ;;
                esac
            fi
        else
            echo "[fail] L0k: CLI tool detected but commands.json missing (R38)"
            echo "[hint] 此软件构建可执行文件, 应在软件级别目录下创建 commands.json:"
            echo "         cp templates/commands.json.template ${COMMANDS_JSON}"
            echo "       参考 archives/s/strace/commands.json 示例"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} commands_json_r38"
        fi
    else
        # 库类型, 不需要 commands.json
        if [ -f "$COMMANDS_JSON" ]; then
            echo "        [warn] L0k: commands.json exists but package looks like a library (no bindirs/bin install)"
        else
            echo "        [ok] library package, commands.json not required"
        fi
    fi
    fi

    # ── L0m: 目录结构校验 (R39) ──
    # archives/ 目录必须遵循 archives/<首字母>/<包名>/<版本>/ 结构
    # 规则 1: 路径层级必须是 4 段 archives/<单字符>/<包名>/<版本>
    # 规则 2: <首字母> 必须等于 <包名> 首字母（小写）
    # 规则 3: <版本> 目录名必须与 conanfile.py 中 version = "..." 一致
    echo "[step] L0m: Checking directory structure (R39)..."
    STRUCTURE_CHECK=$(python3 - "$pkg_dir" "$REPO_ROOT" "$CONANFILE" <<'PYEOF'
import os, re, sys
pkg_dir, repo_root, conanfile = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    rel = os.path.relpath(pkg_dir, repo_root).replace("\\", "/")
except ValueError:
    print("ERR|无法计算相对路径")
    sys.exit(0)
parts = rel.split("/")
if len(parts) != 4 or parts[0] != "archives":
    print(f"ERR|目录层级不是 archives/<首字母>/<包名>/<版本>/，实际: {rel}")
    sys.exit(0)
letter, pkg_name, pkg_ver = parts[1], parts[2], parts[3]
if len(letter) != 1 or not letter.isalnum():
    print(f"ERR|首字母目录 '{letter}' 不是单字符（应为 {pkg_name[0].lower() if pkg_name else '?'}）")
    sys.exit(0)
if letter.lower() != pkg_name[0].lower():
    print(f"ERR|首字母目录 '{letter}' 与包名 '{pkg_name}' 首字母 '{pkg_name[0].lower()}' 不一致")
    sys.exit(0)
try:
    text = open(conanfile, encoding="utf-8", errors="replace").read()
    m = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if m and pkg_ver != m.group(1):
        print(f"ERR|版本目录 '{pkg_ver}' 与 conanfile.py version='{m.group(1)}' 不一致")
        sys.exit(0)
except Exception:
    pass  # conanfile.py 读不了由 L0b 处理
print("OK")
PYEOF
)
    if [ "${STRUCTURE_CHECK%%|*}" = "ERR" ]; then
        ERR_MSG="${STRUCTURE_CHECK#*|}"
        echo "[fail] L0m: 目录结构不合规 (R39): ${ERR_MSG}"
        echo "[hint] 正确格式: archives/<首字母>/<包名>/<版本号>/conanfile.py"
        echo "       例如: archives/f/fnt/1.9.1/conanfile.py"
        echo "       不要用 'homebrew' 等非版本号字符串作为版本目录名"
        L0_FAILED=true
        L0_ERRORS="${L0_ERRORS} dir_structure_r39"
    else
        echo "        [ok] L0m: directory structure valid"
    fi

    # ── L0n: 分支名与包名-版本匹配校验 (R40) ──
    # 分支名剥掉可选前缀（如 feat/）后必须精确等于 {pkg_name}-{pkg_ver}
    #   通过: abc-1.0.0 / feat/abc-1.0.0 / fix/abc-1.0.0
    #   拦截: abc-1.0.0-ASDH（带后缀，平台任务按分支名完全一致匹配会关联失败）
    # 归一化：+ → -（Debian 风格版本后缀如 1.4+dfsg.1 → 1.4-dfsg.1）
    # REL 构建或 main/master/server 分支自动跳过
    # PR > 5200: 强制失败（报错）; PR <= 5200: 仅告警（历史 PR 宽容）
    if [ -n "${CI_BRANCH:-}" ] && [ "${CI_BRANCH}" != "main" ] \
       && [ "${CI_BRANCH}" != "master" ] && [ "${CI_BRANCH}" != "server" ]; then
        echo "[step] L0n: Checking branch name matches package (R40)..."
        EXPECTED_TAG="${pkg_name}-${pkg_ver}"
        EXPECTED_TAG_NORM=$(echo "${EXPECTED_TAG}" | tr '+' '-')
        BRANCH_NORM=$(echo "${CI_BRANCH}" | tr '+' '-')
        # 剥掉最后一段 '/' 前缀（允许 feat/ fix/ adapt/ 等任意前缀，禁止任何后缀）
        BRANCH_BASE="${BRANCH_NORM##*/}"
        if [ "${BRANCH_BASE}" = "${EXPECTED_TAG_NORM}" ]; then
            echo "        [ok] L0n: branch '${CI_BRANCH}' matches '${EXPECTED_TAG}' exactly (prefix allowed)"
        else
            # PR > 5200 强制失败, PR <= 5200 仅告警
            _pr_num="${CI_PR_NUMBER:-0}"
            if [ "${_pr_num}" -gt 5200 ] 2>/dev/null; then
                echo "[error] L0n: branch name mismatch (R40) — 分支名（去掉前缀后）不等于 包名-版本号"
                echo "       分支 '${CI_BRANCH}'（去前缀后 '${BRANCH_BASE}'）≠ '${EXPECTED_TAG}'"
                echo "[hint] 分支名必须以 包名-版本号 结尾，不允许加任何后缀，例如："
                echo "         ${pkg_name}-${pkg_ver}"
                echo "         feat/${pkg_name}-${pkg_ver}"
                echo "         fix/${pkg_name}-${pkg_ver}"
                echo "       ❌ 错误示例: ${pkg_name}-${pkg_ver}-ASDH / ${pkg_name}-${pkg_ver}_2"
                echo "       平台按 分支名完全一致 + 作者 匹配任务，分支名有后缀会导致任务无法关联"
                L0_FAILED=true
                L0_ERRORS="${L0_ERRORS} branch_name_r40"
            else
                echo "[warn] L0n: branch name mismatch (R40) — PR #${_pr_num} <= 5200, 仅告警不拦截"
                echo "       分支 '${CI_BRANCH}'（去前缀后 '${BRANCH_BASE}'）≠ '${EXPECTED_TAG}'"
                echo "[hint] 分支名必须以 包名-版本号 结尾（允许 feat/ 等前缀，禁止后缀）"
            fi
        fi
    fi

    # L0o: 禁止使用外部网络命令下载源码 (防 uses_external_curl)
    # conanfile.py 的 build() 方法禁止调用 curl/wget 下载
    if [ -f "$CONANFILE" ]; then
        EXT_CURL=$(grep -nE '(subprocess|os\.system).*?(curl|wget)|"curl"|"wget"|'"'"'curl'"'"'|'"'"'wget'"'"'' "$CONANFILE" 2>/dev/null | grep -v '^\s*#' | grep -v 'tools\.\|conan_data\|self\.run\|#.*curl\|#.*wget' || true)
        if [ -n "$EXT_CURL" ]; then
            echo "[fail] L0o: conanfile.py 使用外部命令 (curl/wget) 下载源码 — CI 环境可能无 curl"
            echo "       ${EXT_CURL%%$'\n'*}"
            echo "[hint] 必须用 self.conan_data 或 tools.files.get() 下载源码"
            L0_FAILED=true
            L0_ERRORS="${L0_ERRORS} uses_external_curl"
        fi
    fi

    # L0p: settings 必须包含 os/compiler/build_type/arch 四项 (防 profile 不兼容)
    if [ -f "$CONANFILE" ]; then
        SETTINGS_LINE=$(grep -E '^\s*settings\s*=' "$CONANFILE" 2>/dev/null | head -1 || true)
        if [ -n "$SETTINGS_LINE" ]; then
            for req in "os" "compiler" "build_type" "arch"; do
                if ! echo "$SETTINGS_LINE" | grep -q "\"$req\"\|'$req'\|\b${req}\b"; then
                    echo "[fail] L0p: settings 缺少 '$req' — OHOS profile 需要全部四项"
                    echo "       当前: ${SETTINGS_LINE}"
                    echo "[hint] settings = \"os\", \"compiler\", \"build_type\", \"arch\""
                    L0_FAILED=true
                    L0_ERRORS="${L0_ERRORS} missing_setting_${req}"
                fi
            done
        fi
    fi

    # L0q: exports_sources 必须包含 conanfile.py 和 patches/ (防 recipe_not_exported)
    if [ -f "$CONANFILE" ]; then
        # 只在 conanfile.py 引用了 patches 时检查
        if grep -q 'patches/' "$CONANFILE" 2>/dev/null || [ -d "$pkg_dir/patches" ]; then
            ES_LINE=$(grep -E '^\s*exports_sources\s*=' "$CONANFILE" 2>/dev/null | head -1 || true)
            if [ -n "$ES_LINE" ]; then
                # 检查是否包含通配符 *（涵盖 patches/）
                if ! echo "$ES_LINE" | grep -q '\*' 2>/dev/null; then
                    # 没有通配符，检查是否显式包含 patches
                    if [ -d "$pkg_dir/patches" ]; then
                        PATCH_COUNT=$(find "$pkg_dir/patches" -name '*.patch' -o -name '*.diff' 2>/dev/null | wc -l)
                        if [ "$PATCH_COUNT" -gt 0 ] && ! echo "$ES_LINE" | grep -qi 'patch' 2>/dev/null; then
                            echo "[warn] L0q: exports_sources 可能未包含 patches/ — conan create 导出时可能丢失补丁"
                            echo "       exports_sources: ${ES_LINE}"
                            echo "       patches/ 目录有 ${PATCH_COUNT} 个补丁文件"
                            echo "[hint] exports_sources 应包含补丁文件，或使用通配符"
                        fi
                    fi
                fi
            fi
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

    # ── Knowledge graph quality check (KC) ──
    # 运行知识库质量门禁（纯 shell，CI-safe）
    # 检查草稿泄漏、模板占位符、auto_fix 格式、非标准字段、index 一致性
    if [ -f "${REPO_ROOT}/ci/scripts/knowledge_check.sh" ]; then
        echo ""
        echo "[step] KC: Knowledge graph quality check..."
        if bash "${REPO_ROOT}/ci/scripts/knowledge_check.sh" "${REPO_ROOT}" 2>&1; then
            echo "        [ok] KC: knowledge check passed"
        else
            echo "[fail] KC: knowledge check failed — blocking build"
            L0_RESULT="fail"
            L0_DETAIL="knowledge_check failed"
            echo "L0_RESULT=${L0_RESULT}: ${L0_DETAIL}"
            echo "L1_RESULT=skip: blocked_by_KC"
            echo "L2_RESULT=skip: blocked_by_KC"
            echo "L4_RESULT=skip: blocked_by_KC"
            echo "L5_RESULT=skip: blocked_by_KC"
            FAILED=$((FAILED + 1))
            FAILED_PKGS+=("${pkg_name}/${pkg_ver} (KC gate)")
            continue
        fi
    fi

    # ── Junk file check (JC) ──
    # 拦截运行时状态文件、二进制产物、源码 tarball、临时构建产物
    if [ -f "${REPO_ROOT}/ci/scripts/junk_check.sh" ]; then
        echo ""
        echo "[step] JC: Junk file check..."
        if bash "${REPO_ROOT}/ci/scripts/junk_check.sh" "${REPO_ROOT}" 2>&1; then
            echo "        [ok] JC: no junk files detected"
        else
            echo "[fail] JC: junk files detected — blocking build"
            L0_RESULT="fail"
            L0_DETAIL="junk_check failed"
            echo "L0_RESULT=${L0_RESULT}: ${L0_DETAIL}"
            echo "L1_RESULT=skip: blocked_by_JC"
            echo "L2_RESULT=skip: blocked_by_JC"
            echo "L4_RESULT=skip: blocked_by_JC"
            echo "L5_RESULT=skip: blocked_by_JC"
            FAILED=$((FAILED + 1))
            FAILED_PKGS+=("${pkg_name}/${pkg_ver} (JC gate)")
            continue
        fi
    fi

    # ── Mirror fallback (通用镜像映射) ──
    # 将 conandata.yml 中已知域名的 url 从单值改为列表, 自动加上镜像源 fallback
    # Conan 2.x 的 get() 支持 url 列表, 会逐个尝试直到成功
    # 支持: github.com, ftpmirror.gnu.org, ftp.gnu.org, download.savannah.gnu.org
    # 支持: archives.boost.io, download.gnome.org, gitlab.gnome.org, cdn.kernel.org
    # 支持: files.pythonhosted.org, release-assets.githubusercontent.com
    # 支持: sourceforge.net, bbuseruploads.s3.amazonaws.com, curl.se
    if [ -f "$CONANDATA" ]; then
        if grep -qE 'url:.*https://(archives\.boost\.io|github\.com|ftpmirror\.gnu\.org|ftp\.gnu\.org|download\.savannah\.gnu\.org|download\.gnome\.org|gitlab\.gnome\.org|cdn\.kernel\.org|files\.pythonhosted\.org|release-assets\.githubusercontent\.com|[a-z0-9.-]+\.dl\.sourceforge\.net|sourceforge\.net|bbuseruploads\.s3\.amazonaws\.com|curl\.se|ftp\.jaist\.ac\.jp)/' "$CONANDATA" 2>/dev/null; then
            echo "[step] Mirror fallback: rewriting source URLs in conandata.yml..."
            cp "$CONANDATA" "${CONANDATA}.orig" 2>/dev/null

            python3 - "$CONANDATA" <<'PYEOF'
import re, sys

path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

def get_mirrors(url):
    """根据 URL 域名返回镜像列表（含原始 URL）。
    p 包含完整路径（含 /gnu/ 等子路径），镜像 URL 用根路径拼接。
    """
    # ── archives.boost.io → SourceForge (官方源慢, SF 国内可达 600KB/s) ──
    if re.match(r'^https?://archives\.boost\.io/release/([\d.]+)/source/(.+)$', url):
        ver, fn = re.match(r'^https?://archives\.boost\.io/release/([\d.]+)/source/(.+)$', url).groups()
        sf = f'https://downloads.sourceforge.net/project/boost/boost/{ver}/{fn}'
        return [sf, url]
    # ── GitHub ──
    # 实测（2026-08-06）：仅 gh-proxy.com 可用（412KB/s），其余全部失效
    # github.com 直连可用但极慢（19KB/s），作为最后兜底
    if re.match(r'^https?://github\.com/', url):
        return [
            'https://gh-proxy.com/' + url,
            url,
        ]
    # ── GNU (ftpmirror.gnu.org) ──
    if re.match(r'^https?://ftpmirror\.gnu\.org/', url):
        p = re.sub(r'^https?://ftpmirror\.gnu\.org/', '', url)
        return [
            'https://mirrors.tuna.tsinghua.edu.cn/' + p,
            'https://mirrors.ustc.edu.cn/' + p,
            'https://mirrors.aliyun.com/' + p,
            'https://ftp.gnu.org/' + p,
            url,
        ]
    # ── GNU (ftp.gnu.org) ──
    if re.match(r'^https?://ftp\.gnu\.org/', url):
        p = re.sub(r'^https?://ftp\.gnu\.org/', '', url)
        return [
            'https://mirrors.tuna.tsinghua.edu.cn/' + p,
            'https://mirrors.ustc.edu.cn/' + p,
            'https://mirrors.aliyun.com/' + p,
            url,
        ]
    # ── GNU Savannah (download.savannah.gnu.org) ──
    if re.match(r'^https?://download\.savannah\.gnu\.org/', url):
        p = re.sub(r'^https?://download\.savannah\.gnu\.org/', '', url)
        return [
            'https://mirrors.tuna.tsinghua.edu.cn/savannah/' + p,
            url,
        ]
    # ── GNOME (download.gnome.org) ──
    if re.match(r'^https?://download\.gnome\.org/', url):
        p = re.sub(r'^https?://download\.gnome\.org/', '', url)
        return [
            'https://mirrors.ustc.edu.cn/gnome/' + p,
            'https://mirrors.tuna.tsinghua.edu.cn/gnome/' + p,
            'https://mirror.nju.edu.cn/gnome/' + p,
            url,
        ]
    # ── GNOME GitLab (gitlab.gnome.org) — GitHub proxy 兼容 ──
    if re.match(r'^https?://gitlab\.gnome\.org/', url):
        return [
            url,
        ]
    # ── kernel.org CDN (cdn.kernel.org / cdn.kernel.org/pub/linux/kernel/) ──
    if re.match(r'^https?://cdn\.kernel\.org/', url):
        p = re.sub(r'^https?://cdn\.kernel\.org/', '', url)
        return [
            'https://mirrors.ustc.edu.cn/kernel.org/' + p,
            'https://mirrors.tuna.tsinghua.edu.cn/' + p,
            'https://mirror.nju.edu.cn/' + p,
            url,
        ]
    # ── Python packages (files.pythonhosted.org) ──
    # conandata.yml 不太可能引用这里, 但以防万一
    if re.match(r'^https?://files\.pythonhosted\.org/', url):
        return [
            url,
        ]
    # ── GitHub release assets (release-assets.githubusercontent.com) ──
    if re.match(r'^https?://[^/]*release-assets\.githubusercontent\.com/', url):
        return [
            'https://gh-proxy.com/' + url,
            'https://mirror.ghproxy.com/' + url,
            url,
        ]
    # ── SourceForge ──
    if re.match(r'^https?://(downloads\.|[^/]*\.dl\.)?sourceforge\.net/', url):
        # SourceForge 国内有镜像但 URL 结构不同, 保留原始 URL + 加一个 downloads URL
        return [
            url,
        ]
    # ── curl.se (原 haxx.se) ──
    if re.match(r'^https?://curl\.se/', url):
        return [
            url,
        ]
    # ── 无匹配镜像 ──
    return [url]

def replace_url(match):
    indent = match.group(1)
    quote = match.group(2)
    url = match.group(3)
    mirrors = get_mirrors(url)
    if len(mirrors) <= 1:
        return match.group(0)  # 无镜像，保持原样
    subindent = indent + '  '
    lines = [indent + 'url:'] + [subindent + '- ' + quote + m + quote for m in mirrors]
    return '\n'.join(lines)

# 匹配单值 url: "https://..." (不处理已经是列表的)
pattern = r'^([ \t]*)url:[ \t]*(["\'])(https?://[^\s"\']+)\2[ \t]*$'
content = re.sub(pattern, replace_url, content, flags=re.MULTILINE)

with open(path, 'w') as f:
    f.write(content)
PYEOF

            echo "        [ok] Source URLs rewritten with mirror fallback"
        fi
    fi

    # ── Pre-download source archives with retry ──
    # Conan get() 对每个 URL 只试一次。如果 gh-proxy.com 和 github.com 同时不可达,
    # 构建直接失败。这里在 conan build 之前先提取所有源码 URL,
    # 用 curl --retry 下载到本地, 然后把 conandata.yml 改为 file:// 路径。
    if [ -f "$CONANDATA" ]; then
        echo "[step] Pre-download: extracting source URLs from conandata.yml..."

        # 创建预下载缓存目录
        BUILD_DIR="${BUILD_DIR:-${REPO_ROOT}/.build-cache}"
        PREDL_DIR="${BUILD_DIR}/predl_cache"
        mkdir -p "$PREDL_DIR"

        python3 - "$CONANDATA" "$PREDL_DIR" <<'PYEOF'
import re, sys, os, hashlib, subprocess

conandata_path = sys.argv[1]
predl_dir = sys.argv[2]

with open(conandata_path, 'r') as f:
    raw = f.read()

# 解析所有 URL（包括已改写为列表的）
# 匹配: url: https://... 或 - https://...
url_pattern = r'(?:^|\s)(?:url:?\s*)?["\']?-?\s*(https?://[^\s"\'-]+)'
urls = re.findall(url_pattern, raw, re.MULTILINE)
# 去重
urls = list(dict.fromkeys(urls))

if not urls:
    print("  no URLs found in conandata.yml")
    sys.exit(0)

print(f"  found {len(urls)} source URL(s)")

def get_mirror_list(url):
    """返回镜像列表（和 build_and_test.sh get_mirrors 一致）。"""
    mirrors = []
    if re.match(r'^https?://github\.com/', url):
        mirrors = ['https://gh-proxy.com/' + url, url]
    elif re.match(r'^https?://[^/]*release-assets\.githubusercontent\.com/', url):
        mirrors = ['https://gh-proxy.com/' + url, url]
    elif re.match(r'^https?://ftpmirror\.gnu\.org/', url):
        p = re.sub(r'^https?://ftpmirror\.gnu\.org/', '', url)
        mirrors = [f'https://mirrors.tuna.tsinghua.edu.cn/{p}',
                   f'https://mirrors.ustc.edu.cn/{p}',
                   f'https://mirrors.aliyun.com/{p}', url]
    elif re.match(r'^https?://download\.gnome\.org/', url):
        p = re.sub(r'^https?://download\.gnome\.org/', '', url)
        mirrors = [f'https://mirrors.ustc.edu.cn/gnome/{p}',
                   f'https://mirrors.tuna.tsinghua.edu.cn/gnome/{p}',
                   f'https://mirror.nju.edu.cn/gnome/{p}', url]
    elif re.match(r'^https?://cdn\.kernel\.org/', url):
        p = re.sub(r'^https?://cdn\.kernel\.org/', '', url)
        mirrors = [f'https://mirrors.ustc.edu.cn/kernel.org/{p}',
                   f'https://mirrors.tuna.tsinghua.edu.cn/{p}', url]
    else:
        mirrors = [url]
    return mirrors

downloaded = {}
for url in urls:
    # 文件名用 URL 的 hash 防冲突
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    filename = url.split('/')[-1] or f'source_{url_hash}'
    if '?' in filename:
        filename = filename.split('?')[0]
    dest = os.path.join(predl_dir, f'{url_hash}_{filename}')

    if os.path.exists(dest) and os.path.getsize(dest) > 100:
        print(f"  [cached] {filename} ({os.path.getsize(dest)//1024}KB)")
        downloaded[url] = dest
        continue

    mirrors = get_mirror_list(url)
    success = False
    for i, mirror_url in enumerate(mirrors):
        # 每个镜像试 3 次
        for attempt in range(1, 4):
            print(f"  [try {i+1}/{len(mirrors)}.{attempt}/3] {filename} ← {mirror_url[:80]}...")
            try:
                result = subprocess.run(
                    ['curl', '-sL', '--retry', '3', '--retry-delay', '10',
                     '--connect-timeout', '30', '--max-time', '300',
                     '-o', dest, '-w', '%{http_code}:%{size_download}',
                     mirror_url],
                    capture_output=True, text=True, timeout=360
                )
                size = os.path.getsize(dest) if os.path.exists(dest) else 0
                if size > 100:
                    print(f"  [ok] {filename} ({size//1024}KB) via mirror {i+1}")
                    downloaded[url] = dest
                    success = True
                    break
                else:
                    print(f"  [fail] size={size}, http={result.stdout[-3:]}")
            except Exception as e:
                print(f"  [fail] {str(e)[:60]}")
        if success:
            break

    if not success:
        print(f"  [WARN] Failed to pre-download {filename}, will rely on conan's download")

if downloaded:
    # 把 conandata.yml 里的远程 URL 替换为 file:// 本地路径
    with open(conandata_path, 'r') as f:
        content = f.read()

    for url, local_path in downloaded.items():
        content = content.replace(url, f'file://{local_path}')

    with open(conandata_path, 'w') as f:
        f.write(content)
    print(f"  [done] Pre-downloaded {len(downloaded)} files, conandata.yml updated to file:// URLs")
else:
    print("  [done] No files pre-downloaded")
PYEOF
    fi

    # ── Conf compatibility patch (conan 2.29.1 兼容层) ──
    # ConanCenter 配方可能使用上游新版 conf (如 tools.gnu:gcc:ar),
    # 但 OHOS 适配版 conan 2.29.1 未注册这些 conf, 导致 get() 抛异常.
    # 在 conan create 之前, 将这些 conf 调用替换为环境变量读取.
    if [ -f "$CONANFILE" ]; then
        if grep -qE 'tools\.gnu:gcc:(ar|ranlib|nm)' "$CONANFILE" 2>/dev/null; then
            echo "[step] Conf compat: patching tools.gnu:gcc:* references..."
            cp "$CONANFILE" "${CONANFILE}.confbak" 2>/dev/null
            python3 - "$CONANFILE" <<'PYEOF'
import re, sys

path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

# Map: conf name → {replacement value, env var}
conf_map = {
    'tools.gnu:gcc:ar':     {'val': 'llvm-ar',     'env': 'AR'},
    'tools.gnu:gcc:ranlib': {'val': 'llvm-ranlib', 'env': 'RANLIB'},
    'tools.gnu:gcc:nm':     {'val': 'llvm-nm',     'env': 'NM'},
}

for conf, info in conf_map.items():
    # Replace: self.conf.get("tools.gnu:gcc:ar", default="...", check_type=str)
    # With:   os.environ.get("AR", "llvm-ar")
    escaped = re.escape(conf)
    pattern = (
        r'self\.conf\.get\(\s*["\']' + escaped + r'["\']'
        r'(?:\s*,\s*default\s*=\s*[^)]+)?'
        r'(?:\s*,\s*check_type\s*=\s*[^)]+)?\s*\)'
    )
    replacement = f'os.environ.get("{info["env"]}", "{info["val"]}")'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        print(f'  patched: {conf} → os.environ.get("{info["env"]}", "{info["val"]}")')

with open(path, 'w') as f:
    f.write(content)
PYEOF
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
    # Default to 45 minutes. Centrally reviewed high-cost packages may use a
    # bounded override from ci/config/build_timeouts.txt.
    BUILD_TIMEOUT=$(build_timeout_for "${pkg_name}/${pkg_ver}")
    if [ "$BUILD_TIMEOUT" -ne "$DEFAULT_BUILD_TIMEOUT" ]; then
        echo "[step] Extended build timeout for ${pkg_name}/${pkg_ver}: ${BUILD_TIMEOUT}s"
    fi
    BUILD_STARTED_AT=$(date +%s)
    # Disable set -e around conan create — we need to capture the exit code
    # and continue to the next package on failure (BUG: set -e caused premature exit)
    set +e
    timeout --signal=KILL "$BUILD_TIMEOUT" conan create "$pkg_dir" "${CONAN_CREATE_ARGS[@]}" --build="${pkg_name}/*" 2>&1 | tee "$BUILD_LOG"
    PIPE_STATUSES=("${pipestatus[@]}")
    CONAN_RC=${PIPE_STATUSES[1]:-1}
    TEE_RC=${PIPE_STATUSES[2]:-1}
    BUILD_ELAPSED=$(( $(date +%s) - BUILD_STARTED_AT ))
    set -e

    if [ "$TEE_RC" -ne 0 ]; then
        echo "[fail] ${pkg_name}/${pkg_ver} — unable to write complete conan build log (tee rc=${TEE_RC})"
        echo "L0_RESULT=${L0_RESULT}: ${L0_DETAIL}"
        echo "L1_RESULT=fail: conan build log is incomplete"
        echo "L2_RESULT=skip: not run"
        echo "L4_RESULT=skip: not run"
        echo "L5_RESULT=skip: not run"
        FAILED=$((FAILED + 1))
        FAILED_PKGS+=("${pkg_name}/${pkg_ver} (build log)")
        continue
    fi

    # GNU timeout may return 124 or 137. Either code is a timeout only when
    # the configured bound was actually reached; a child may return it early.
    if is_build_timeout_result "$CONAN_RC" "$BUILD_ELAPSED" "$BUILD_TIMEOUT"; then
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
            TEST_COMPILE_LINES=$(grep -cE "(clang|gcc|cc|g\+\+|c\+\+)" "$BUILD_LOG" 2>/dev/null || true)
            TEST_RUN_LINES=$(grep -cE "(\./[a-z]|Running test|PASS|FAIL|ok\b)" "$BUILD_LOG" 2>/dev/null || true)
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
        # Conan 2.x: `conan cache path "name/version"` returns the recipe cache
        # (only conanfile.py + conandata.yml), not the package cache (lib/, include/).
        # Parse the Package folder path from the conan create build log instead.
        # NOTE: 用 awk 单进程替代 grep|tail|sed 管道，彻底消除 SIGPIPE (exit 141) 风险
        #   （zsh + pipefail + set -e 下，grep 写入 tail 管道被提前关闭 → SIGPIPE → exit 141，
        #    trap '' PIPE 和 || true 在 $(...) 子 shell 中不可靠）
        PKG_CACHE=$(awk '/Package folder/{line=$0} END{sub(/.*Package folder /,"",line); print line}' "$BUILD_LOG" 2>/dev/null || true)
        if [ -n "$PKG_CACHE" ] && [ -d "$PKG_CACHE" ]; then
            BINS=$(find "$PKG_CACHE" -name "bin" -type d -print -quit 2>/dev/null)
            LIBS=$(find "$PKG_CACHE" -name "lib" -type d -print -quit 2>/dev/null)
            INCS=$(find "$PKG_CACHE" -name "include" -type d -print -quit 2>/dev/null)

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
            for lib_file in "$LIBS"/*.so*(N); do
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

        # ── L5: SONAME 质量门禁 (防 IMPORTED_NO_SONAME + DT_SONAME 缺失) ──
        # 三条规则（基于 SONAME 存量扫描报告，覆盖 23 个已知缺陷）：
        # L5a: 可链接共享库必须有 DT_SONAME 且为相对路径
        # L5b: DT_NEEDED 条目禁止绝对路径或 ../ 开头
        # L5c: 包内 *.cmake 禁止 IMPORTED_NO_SONAME.*TRUE
        if [ -n "$PKG_CACHE" ] && [ -d "$PKG_CACHE" ]; then
            L5_SONAME_ERRS=0

            # L5a+L5b: ELF 扫描（仅 lib/ 一级目录，排除插件子目录）
            if [ -n "$LIBS" ] && [ -d "$LIBS" ]; then
                for so_file in "$LIBS"/lib*.so(N); do
                    [ -f "$so_file" ] || continue
                    # 排除插件：在 lib/ 子目录中（lib/plugins/, lib/modules/ 等）的不检查
                    so_dir="${so_file:h}"
                    if [ "$so_dir" != "$LIBS" ]; then
                        continue
                    fi

                    so_basename="${so_file:t}"
                    # 跳过 INTERFACE 库的空 stub .so（极少数情况）
                    [ ! -s "$so_file" ] && continue

                    # readelf -d 提取 SONAME 和 NEEDED
                    ELF_INFO=$(readelf -d "$so_file" 2>/dev/null || true)

                    # L5a: 检查 DT_SONAME
                    SONAME_VAL=$(echo "$ELF_INFO" | grep '(SONAME)' | sed 's/.*\[\(.*\)\].*/\1/' || true)
                    if [ -z "$SONAME_VAL" ]; then
                        echo "[fail] L5a: ${so_basename} 缺少 DT_SONAME — 下游链接器无法按 SONAME 寻址"
                        echo "       文件: ${so_file#${PKG_CACHE}}"
                        echo "[hint]  在 CMakeLists.txt 中设置 set_target_properties(... PROPERTIES SOVERSION x.y)"
                        L5_SONAME_ERRS=$((L5_SONAME_ERRS + 1))
                    elif echo "$SONAME_VAL" | grep -q '^/' 2>/dev/null; then
                        echo "[fail] L5a: ${so_basename} 的 DT_SONAME 是绝对路径: ${SONAME_VAL}"
                        L5_SONAME_ERRS=$((L5_SONAME_ERRS + 1))
                    fi

                    # L5b: 检查 DT_NEEDED 禁止绝对路径或 ../
                    BAD_NEEDED=$(echo "$ELF_INFO" | grep '(NEEDED)' | sed 's/.*\[\(.*\)\].*/\1/' | grep -E '^/|^\.\./' || true)
                    if [ -n "$BAD_NEEDED" ]; then
                        echo "[fail] L5b: ${so_basename} 的 DT_NEEDED 含绝对/相对路径: ${BAD_NEEDED}"
                        echo "       文件: ${so_file#${PKG_CACHE}}"
                        L5_SONAME_ERRS=$((L5_SONAME_ERRS + 1))
                    fi
                done
            fi

            # L5c: cmake 文件禁止 IMPORTED_NO_SONAME TRUE
            CMAKE_BAD=$(grep -rl 'IMPORTED_NO_SONAME.*TRUE\|IMPORTED_NO_SONAME.*True\|IMPORTED_NO_SONAME.*true' "${PKG_CACHE}" --include='*.cmake' 2>/dev/null || true)
            if [ -n "$CMAKE_BAD" ]; then
                CMAKE_COUNT=$(echo "$CMAKE_BAD" | wc -l)
                echo "[fail] L5c: ${CMAKE_COUNT} 个 .cmake 文件含 IMPORTED_NO_SONAME TRUE — 下游必须按完整路径链接"
                echo "$CMAKE_BAD" | head -5 | sed "s|^|       |"
                L5_SONAME_ERRS=$((L5_SONAME_ERRS + 1))
            fi

            if [ "$L5_SONAME_ERRS" -gt 0 ]; then
                echo "[fail] L5: SONAME quality gate failed (${L5_SONAME_ERRS} errors)"
                L5_RESULT="fail"
                L5_DETAIL="soname_gate_failed"
            fi
        fi

        # ── L1e: 破坏性反向验证 (R34: test 必须实质依赖被测包) ──
        # 原理: 将被测包产物替换为损坏版本，重新 conan test (重新编译+链接+运行)
        #   仍 PASS = 假测试 (test 不依赖被测包)
        #   FAIL   = 真测试 (链接/运行确实依赖被测包)
        if [ "$L1_RESULT" != "fail" ] && [ -n "$PKG_CACHE" ] && [ -d "$PKG_CACHE" ]; then
            echo "[step] L1e: Destructive negative test (R34)..."

            _BACKUP_DIR="${TMPDIR:-$HOME/tmp}/l1e_backup_${pkg_name}_$$"
            mkdir -p "$_BACKUP_DIR"

            # 破坏策略: mv 整个产物子目录 (而非逐个文件操作)
            # 原因: make install 的文件在鸿蒙下可能只读 (MAC 策略),
            #        但 Conan 创建的 package 目录本身当前用户可写
            _SABOTAGED=0

            # bin/ → 移走 (破坏可执行文件和命令行工具)
            if [ -n "$BINS" ] && [ -d "$BINS" ]; then
                mv "$BINS" "$_BACKUP_DIR/bin" 2>/dev/null && _SABOTAGED=$((_SABOTAGED + 1)) && echo "        [sabotage] bin/ moved away"
            fi

            # lib/ → 移走 (破坏静态库和动态库)
            if [ -n "$LIBS" ] && [ -d "$LIBS" ]; then
                mv "$LIBS" "$_BACKUP_DIR/lib" 2>/dev/null && _SABOTAGED=$((_SABOTAGED + 1)) && echo "        [sabotage] lib/ moved away"
            fi

            # include/ → 移走 (破坏头文件)
            if [ -n "$INCS" ] && [ -d "$INCS" ]; then
                mv "$INCS" "$_BACKUP_DIR/include" 2>/dev/null && _SABOTAGED=$((_SABOTAGED + 1)) && echo "        [sabotage] include/ moved away"
            fi

            # 如果什么都没破坏到, 说明产物结构异常, 跳过 L1e
            if [ "$_SABOTAGED" -eq 0 ]; then
                echo "        [skip] L1e: No standard artifact dirs found to sabotage"
                rm -rf "$_BACKUP_DIR" 2>/dev/null || true
            else

            # 重新 conan test (会重新编译 test_package 源码 + 链接 + 运行)
            # 预期失败: 被 set -e 拦截, 用 || 捕获退出码
            # 用 PROFILE_FILE (文件路径) 而非 CONAN_PROFILE (profile 名称),
            # 与 conan create 的 -pr:h="$PROFILE_FILE" 保持一致
            _NEG_EXIT=0
            conan test "$TEST_PKG_DIR" "${pkg_name}/${pkg_ver}" \
                -pr "$PROFILE_FILE" --build=missing >/dev/null 2>&1 || _NEG_EXIT=$?

            if [ $_NEG_EXIT -eq 0 ]; then
                echo "[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)"
                echo "        test does not depend on ${pkg_name} — must call its API or execute its binary"
                L1_RESULT="fail"
                L1_DETAIL="negative test: test does not depend on package"
                L1_FAILED=true
            else
                echo "[ok] L1e: Negative test confirmed — test genuinely depends on ${pkg_name}"
            fi

            # 恢复产物: mv 目录回原位
            if [ -d "$_BACKUP_DIR/bin" ]; then
                rm -rf "$BINS" 2>/dev/null || true
                mv "$_BACKUP_DIR/bin" "$BINS" 2>/dev/null || true
            fi
            if [ -d "$_BACKUP_DIR/lib" ]; then
                rm -rf "$LIBS" 2>/dev/null || true
                mv "$_BACKUP_DIR/lib" "$LIBS" 2>/dev/null || true
            fi
            if [ -d "$_BACKUP_DIR/include" ]; then
                rm -rf "$INCS" 2>/dev/null || true
                mv "$_BACKUP_DIR/include" "$INCS" 2>/dev/null || true
            fi
            rm -rf "$_BACKUP_DIR" 2>/dev/null || true
            fi  # end _SABOTAGED > 0
        fi

        # ── L2: Minimal smoke test (--version / --help) ──
        echo "[step] L2: Smoke test (version/help check)..."
        if [ -n "$BINS" ] && [ -d "$BINS" ]; then
            _found_exec=false
            for bin_file in "$BINS"/*(N); do
                [ -f "$bin_file" ] || continue
                [ -x "$bin_file" ] || continue
                _found_exec=true
                bin_name="${bin_file##*/}"
                if timeout 15 "$bin_file" --version </dev/null >/dev/null 2>&1; then
                    echo "[ok] L2: $bin_name --version OK"
                    L2_RESULT="pass"
                    if [ -z "$L2_DETAIL" ] || [ "$L2_DETAIL" = "not_run" ]; then
                        L2_DETAIL="$bin_name --version OK"
                    else
                        L2_DETAIL="${L2_DETAIL}, $bin_name --version OK"
                    fi
                elif timeout 15 "$bin_file" --help </dev/null >/dev/null 2>&1; then
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
            SOURCE_URL=$(awk -F'"' '/^\s*url:/{gsub(/^[ \t]*url:[ \t]*/,""); gsub(/"/,""); print; exit}' "$CONANDATA_FILE" 2>/dev/null || echo "")
            SOURCE_SHA256=$(awk -F'"' '/^\s*sha256:/{gsub(/^[ \t]*sha256:[ \t]*/,""); gsub(/"/,""); print; exit}' "$CONANDATA_FILE" 2>/dev/null || echo "")
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

        # ── 错误诊断提示引擎: 读取 hint_rules.json 规则匹配 BUILD_LOG ──
        _SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        _RULES_FILE="${_SCRIPT_DIR}/../config/hint_rules.json"
        if [ -f "$_RULES_FILE" ] && command -v python3 >/dev/null 2>&1; then
            echo ""
            python3 "${_SCRIPT_DIR}/diagnose.py" "$BUILD_LOG" "$_RULES_FILE"
        fi
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
# 通过率：Success / Total，明确标注（Total=0 时显示 N/A，避免除零）
if [ "${#PACKAGES[@]}" -gt 0 ]; then
    pass_rate=$(awk -v s="$SUCCESS" -v t="${#PACKAGES[@]}" 'BEGIN { printf "%.1f%%", s * 100 / t }')
    echo "  Pass rate: ${pass_rate} (${SUCCESS}/${#PACKAGES[@]})"
else
    echo "  Pass rate: N/A (0 packages)"
fi

if [ $FAILED -gt 0 ]; then
    echo "  Failed packages:"
    for p in "${FAILED_PKGS[@]}"; do
        echo "    - $p"
    done
    exit 1
fi

echo "[step] All packages built and tested successfully ✅"
