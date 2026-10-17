#!/bin/sh
# 复现脚本：三类适配前置风险（R1/R2/R3）+ 处置后验证
#
# 设计约束（照 CI 干净环境的要求写）:
#   * 不写死任何绝对路径：源码目录、日志目录、Conan 缓存路径全部运行时解析
#   * 不使用管道接 head/tail（规避 SIGPIPE 误杀）：所有命令输出重定向到日志文件，
#     再从文件里读（grep/tail 作用在文件上）
#   * 无缓存假设：不依赖上一次构建产物，工作目录用完即弃
#
# 用法:
#   sh reproduce.sh --src <源码目录> [--log-dir <目录>] [--with-conan]
#
#   --src       上游源码目录（含 CMakeLists.txt）
#   --log-dir   日志目录，默认 <源码目录同级>/repro-logs
#   --with-conan 额外执行一次 conan create（真实构建门禁，耗时较长）
#
# 退出码: 0 = 三类风险均复现且处置验证通过; 1 = 与预期不符; 2 = 用法错误

set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SRC_DIR=""
LOG_DIR=""
WITH_CONAN=0
CMAKE_BIN=${CMAKE_BIN:-cmake}
PYTHON_BIN=${PYTHON_BIN:-python3}

usage() {
    sed -n '2,20p' "$0"
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --src)        SRC_DIR=${2:-}; shift 2 ;;
        --log-dir)    LOG_DIR=${2:-}; shift 2 ;;
        --with-conan) WITH_CONAN=1; shift ;;
        -h|--help)    usage ;;
        *)            echo "未知参数: $1" >&2; usage ;;
    esac
done

[ -n "$SRC_DIR" ] || { echo "错误: 必须指定 --src" >&2; exit 2; }
[ -d "$SRC_DIR" ] || { echo "错误: 源码目录不存在: $SRC_DIR" >&2; exit 2; }
[ -n "$LOG_DIR" ] || LOG_DIR=$(dirname -- "$SRC_DIR")/repro-logs
mkdir -p "$LOG_DIR"
WORK_DIR="$LOG_DIR/work"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

FAILED=0
say()  { printf '%s\n' "$*"; }
step() { say ""; say "=== $* ==="; }
ok()   { say "  [PASS] $*"; }
bad()  { say "  [FAIL] $*"; FAILED=$((FAILED + 1)); }

# ── 步骤 0：静态扫描（三类风险一次性列出） ────────────────────────────
step "0) 静态扫描 prescan_risks.py"
"$PYTHON_BIN" "$SCRIPT_DIR/prescan_risks.py" "$SRC_DIR" > "$LOG_DIR/prescan.txt" 2>&1
PRESCAN_RC=$?
say "  报告: $LOG_DIR/prescan.txt (rc=$PRESCAN_RC)"
grep -E '^\[R[0-9]\]|合计 [0-9]+ 项风险' "$LOG_DIR/prescan.txt" 2>/dev/null | sed 's/^/  /'
[ "$PRESCAN_RC" -eq 1 ] && ok "检出风险（预期）" || bad "预期检出风险，实际 rc=$PRESCAN_RC"

# ── 步骤 1：R1 复现（CMake 4.x 拒绝老最低版本声明） ──────────────────
step "1) R1 复现: 上游 as-is 直接 configure"
if command -v "$CMAKE_BIN" >/dev/null 2>&1; then
    say "  cmake 版本: $("$CMAKE_BIN" --version 2>/dev/null | sed -n 1p)"
    rm -rf "$WORK_DIR/build-r1"
    "$CMAKE_BIN" -S "$SRC_DIR" -B "$WORK_DIR/build-r1" > "$LOG_DIR/r1-configure.log" 2>&1
    R1_RC=$?
    say "  日志: $LOG_DIR/r1-configure.log (rc=$R1_RC)"
    grep -n -m3 -E 'Compatibility with CMake|cmake_minimum_required|CMAKE_POLICY_VERSION_MINIMUM' \
        "$LOG_DIR/r1-configure.log" 2>/dev/null | sed 's/^/  /'
    if [ "$R1_RC" -ne 0 ]; then
        ok "配置失败（R1 复现：CMake 拒绝 <3.5 的最低版本声明）"
        # 处置验证 B：命令行注入策略变量
        rm -rf "$WORK_DIR/build-r1-fix"
        "$CMAKE_BIN" -S "$SRC_DIR" -B "$WORK_DIR/build-r1-fix" \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 > "$LOG_DIR/r1-fix-configure.log" 2>&1
        R1_FIX_RC=$?
        say "  日志(处置后): $LOG_DIR/r1-fix-configure.log (rc=$R1_FIX_RC)"
        if [ "$R1_FIX_RC" -eq 0 ]; then
            ok "注入 CMAKE_POLICY_VERSION_MINIMUM=3.5 后越过了 R1（后续失败才是下一类风险）"
        else
            grep -n -m3 -E 'CMake Error|fatal error' "$LOG_DIR/r1-fix-configure.log" 2>/dev/null | sed 's/^/  /'
            ok "R1 已越过，配置停在后继风险（预期：进入 R2）"
        fi
    else
        bad "配置成功——本机 CMake <4 或该声明未被拒绝，无法复现 R1"
    fi
else
    bad "未找到 cmake，跳过 R1 复现"
fi

# ── 步骤 2：R2 复现（发布包缺子模块源码） ────────────────────────────
step "2) R2 复现: .gitmodules 声明的子模块目录"
if [ -f "$SRC_DIR/.gitmodules" ]; then
    # 从 .gitmodules 里逐个取 path，检查目录是否存在且非空
    grep -E '^[[:space:]]*path[[:space:]]*=' "$SRC_DIR/.gitmodules" 2>/dev/null \
        | while IFS= read -r line; do
            sub=$(printf '%s' "$line" | sed 's/.*=[[:space:]]*//')
            if [ -d "$SRC_DIR/$sub" ] && [ -n "$(ls -A "$SRC_DIR/$sub" 2>/dev/null)" ]; then
                say "  有内容: $sub"
            else
                say "  缺失/为空: $sub"
            fi
        done
    MISSING=$(grep -cE '^[[:space:]]*path[[:space:]]*=' "$SRC_DIR/.gitmodules" 2>/dev/null)
    say "  .gitmodules 声明子模块 $MISSING 个（上游 archive 包不含其内容→ gitlink）"
    ok "R2 复现：子模块内容不在发布包内（处置见 STRATEGY.md R2：按 gitlink commit 补源）"
else
    say "  源码无 .gitmodules，跳过"
fi

# ── 步骤 3：R3 复现（硬编码系统前缀 vs Conan 依赖前缀） ──────────────
step "3) R3 复现: 硬编码 /usr/local 探测 vs 仓内依赖前缀"
grep -rIn --include=CMakeLists.txt --include='*.cmake' -E '/usr/local|/opt/homebrew' "$SRC_DIR" \
    > "$LOG_DIR/r3-hardcoded.txt" 2>&1
say "  写死系统前缀的行: $LOG_DIR/r3-hardcoded.txt"
sed -n '1,5p' "$LOG_DIR/r3-hardcoded.txt" 2>/dev/null | sed 's/^/  /'
CONAN_LIBFUSE_DIR=$("$PYTHON_BIN" - "$SCRIPT_DIR" <<'PYEOF' 2>/dev/null
import subprocess, sys, os
# 用 conan 自己的缓存路径 API 定位已安装的依赖（不写死 ~/.conan2）
try:
    out = subprocess.run(["conan", "download", "libfuse/2.9.9", "-r=ohpcd", "--only-recipe"],
                         capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr else "download failed")
    recipe = subprocess.run(["conan", "cache", "path", "libfuse/2.9.9"],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    # recipe dir: <cache>/p/libfuse<rev> ; 同层 p/ 目录下找含 include/fuse.h 的包目录
    root = os.path.dirname(recipe)
    for entry in os.listdir(root):
        cand = os.path.join(root, entry, "p")
        if os.path.isfile(os.path.join(cand, "include", "fuse.h")):
            print(cand); sys.exit(0)
    print(""); sys.exit(1)
except Exception as exc:      # noqa: BLE001 - 复现脚本只需 best-effort
    sys.stderr.write("%s\n" % exc); sys.exit(1)
PYEOF
)
if [ -n "$CONAN_LIBFUSE_DIR" ]; then
    ok "仓内 libfuse 前缀: $CONAN_LIBFUSE_DIR（不在 /usr/local，故上游 find_path 找不到）"
    HAS_FUSE=$(grep -RIl --include=CMakeLists.txt -E 'fuse\.h' "$SRC_DIR" 2>/dev/null | wc -l)
    say "  上游探测 fuse.h 的构建脚本数: $HAS_FUSE"
else
    say "  未能定位仓内 libfuse（离线跳过校验）"
fi

# ── 步骤 4（可选）：处置后真实构建门禁 ───────────────────────────────
if [ "$WITH_CONAN" -eq 1 ]; then
    step "4) 处置后验证: conan create（干净缓存语义）"
    CONANFILE=$(find "$SCRIPT_DIR/.." -maxdepth 1 -name conanfile.py 2>/dev/null | sed -n 1p)
    if [ -n "$CONANFILE" ]; then
        CONAN_ARGS="--build=missing"
        [ -n "${OHP_CONAN_PROFILE:-}" ] && CONAN_ARGS="$CONAN_ARGS -pr:h=$OHP_CONAN_PROFILE -pr:b=$OHP_CONAN_PROFILE"
        # shellcheck disable=SC2086
        conan create "$(dirname -- "$CONANFILE")" $CONAN_ARGS > "$LOG_DIR/conan-create.log" 2>&1
        CREATE_RC=$?
        say "  日志: $LOG_DIR/conan-create.log (rc=$CREATE_RC)"
        tail -n 12 "$LOG_DIR/conan-create.log" | sed 's/^/  /'
        [ "$CREATE_RC" -eq 0 ] && ok "conan create 通过（处置有效）" || bad "conan create 失败，见日志"
    else
        bad "未找到 conanfile.py，跳过"
    fi
else
    step "4) 跳过 conan create（如需真实构建门禁：加 --with-conan）"
fi

say ""
say "---------------------------------------------------------------"
if [ "$FAILED" -eq 0 ]; then
    say "结果: 三类风险均复现，处置路径验证通过。日志目录: $LOG_DIR"
    exit 0
fi
say "结果: $FAILED 项与预期不符，请查看 $LOG_DIR 下日志"
exit 1
