#!/data/service/hnp/bin/bash
# reproduce.sh — KB-ATBOOT 复现脚本：样例库（srf 0.1）两阶段验证
#
# 阶段 ①不启用 SKILL：configure 直接跑，复现 "cannot guess build type" 原始报错
# 阶段 ②启用 SKILL：detect -> fix -> configure，编译通过
#
# ⚠ SIGPIPE 规避铁律：
#   - 所有命令输出重定向到日志文件，绝不 `cmd | head`（SIGPIPE 会杀掉整条管道，
#     掩盖真实退出码，conan/CI 环境下表现为莫名 FAIL）
#   - 退出码从日志文件与 $? 采集，不在管道里判
#
# 用法：reproduce.sh [--sample <目录>] [--keep] [--json]
#   --sample  指定样例库源码目录（默认自动解包内嵌 URL；或用 KB_ATBOOT_SAMPLE 覆盖）
#   --keep    保留工作目录（默认脚本结束清理）
#   --json    机器可读结果输出到 stdout（人读日志走文件+stderr）
#
# OHOS aarch64：clang 用项目内置工具链（/data/service/hnp/bin/clang），
# 通过环境变量 CC 可覆盖；脚本自身不写死任何本地缓存路径。

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK="${TMPDIR:-$PWD}/kb-atboot-repro.$$"
SAMPLE=""
KEEP=0
JSON=0
while [ $# -gt 0 ]; do
    case "$1" in
        --sample) SAMPLE="$2"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        --json) JSON=1; shift ;;
        *) echo "unknown arg: $1" >&2; exit 64 ;;
    esac
done

LOG="$WORK/repro.log"
RESULT_JSON="$WORK/result.json"
mkdir -p "$WORK"
: > "$LOG"

say() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }
fail() { say "FAIL: $*"; }
pass() { say "PASS: $*"; }

cleanup() { [ "$KEEP" -eq 1 ] || rm -rf "$WORK"; }
trap cleanup EXIT

# ---------- 样例库准备 ----------
if [ -z "$SAMPLE" ]; then
    SAMPLE="${KB_ATBOOT_SAMPLE:-}"
fi
if [ -z "$SAMPLE" ] || [ ! -d "$SAMPLE" ]; then
    # 默认样例：srf 0.1（Debian 官方池 orig tarball，PF7 合规）
    SAMPLE_URL="https://deb.debian.org/debian/pool/main/s/srf/srf_0.1+dfsg.orig.tar.gz"
    TARBALL="$WORK/srf.tar.gz"
    say "downloading sample srf 0.1 from Debian pool..."
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$TARBALL" "$SAMPLE_URL" >> "$LOG" 2>&1 || { fail "curl download"; exit 1; }
    else
        fail "no curl available"; exit 1
    fi
    mkdir -p "$WORK/src"
    tar -xzf "$TARBALL" -C "$WORK/src" >> "$LOG" 2>&1 || { fail "untar"; exit 1; }
    SAMPLE="$(find "$WORK/src" -maxdepth 2 -name configure -type f | head -1 | xargs -r dirname)"
    [ -z "$SAMPLE" ] && { fail "no configure dir found after untar"; exit 1; }
fi
say "sample: $SAMPLE"

PHASE1_RC=""
PHASE1_LOG="$WORK/phase1-configure.log"
PHASE2_RC=""
PHASE2_LOG="$WORK/phase2-configure.log"

CC_BIN="${CC:-/data/service/hnp/bin/clang}"
CXX_BIN="${CXX:-/data/service/hnp/bin/clang++}"

# E046/HMDFS 配套规避（与 commoncpp2/io_lib 0002 补丁同源）：
# 老 config.status 用 umask 077 建 ./confXXXX 临时目录，HMDFS 下 700 目录
# 不可写（chmod 被忽略），会淹没真实报错。umask 022 让临时目录可写，
# 从而暴露 KB-ATBOOT 针对的 cannot-guess / Makefile 缺失特征。
umask 022
export TMPDIR="${TMPDIR:-$WORK/tmp}"
mkdir -p "$TMPDIR"

# ---------- 阶段 ①：不启用 SKILL，复现原始报错 ----------
PHASE1_DIR="$WORK/phase1"
cp -r "$SAMPLE" "$PHASE1_DIR"
say "phase1: run configure WITHOUT skill fix"
(
    cd "$PHASE1_DIR"
    CC="$CC_BIN" ./configure --prefix="$WORK/prefix1" > "$PHASE1_LOG" 2>&1
) </dev/null
PHASE1_RC=$?
say "phase1 configure rc=$PHASE1_RC"
# 复现判定（老 autotools 包 configure 常假成功 rc=0，实际 config.status 半途失败）：
#   a) rc!=0 且日志含 cannot-guess 类特征，或
#   b) rc==0 但 Makefile 未生成（config.status 写临时文件失败等）
MAKES_OK=1
for mk in Makefile src/Makefile; do
    [ -f "$PHASE1_DIR/$mk" ] || MAKES_OK=0
done
if { [ "$PHASE1_RC" -ne 0 ] && grep -qE "cannot guess build type|unable to guess|Invalid configuration" "$PHASE1_LOG" 2>/dev/null; } \
   || [ "$MAKES_OK" -eq 0 ]; then
    pass "phase1 reproduced bootstrap failure (rc=$PHASE1_RC, makefiles_ok=$MAKES_OK)"
    PHASE1_VERDICT="reproduced"
else
    fail "phase1 did not reproduce cannot-guess (rc=$PHASE1_RC); see $PHASE1_LOG"
    PHASE1_VERDICT="not-reproduced"
fi

# ---------- 阶段 ②：启用 SKILL（detect -> fix -> configure） ----------
PHASE2_DIR="$WORK/phase2"
cp -r "$SAMPLE" "$PHASE2_DIR"
say "phase2: run configure WITH skill fix"
"$SCRIPT_DIR/detect.sh" --src "$PHASE2_DIR" >> "$LOG" 2>&1
DETECT_RC=$?
say "detect rc=$DETECT_RC"
if [ "$DETECT_RC" -eq 0 ]; then
    pass "detect: no hit (sample unexpectedly clean)"
    PHASE2_VERDICT="no-hit-clean-sample"
else
    "$SCRIPT_DIR/fix.sh" --src "$PHASE2_DIR" >> "$LOG" 2>&1
    FIX_RC=$?
    say "fix rc=$FIX_RC"
    if [ "$FIX_RC" -ne 0 ]; then
        fail "fix.sh rc=$FIX_RC"
        PHASE2_VERDICT="fix-failed"
    else
        (
            cd "$PHASE2_DIR"
            CC="$CC_BIN" ./configure --prefix="$WORK/prefix2" > "$PHASE2_LOG" 2>&1
        ) </dev/null
        PHASE2_RC=$?
        say "phase2 configure rc=$PHASE2_RC"
        if [ "$PHASE2_RC" -eq 0 ]; then
            pass "phase2 configure passed after fix"
            PHASE2_VERDICT="fixed"
        else
            # srf 这类 2008 库 configure 过了还可能因后续依赖失败；
            # 判定口径：cannot-guess 错误必须消失
            if grep -qE "cannot guess build type|unable to guess" "$PHASE2_LOG" 2>/dev/null; then
                fail "phase2 still cannot-guess after fix"
                PHASE2_VERDICT="fix-ineffective"
            else
                pass "phase2: cannot-guess eliminated (rc=$PHASE2_RC, later failure is out of KB-ATBOOT scope)"
                PHASE2_VERDICT="fixed-later-failure-out-of-scope"
            fi
        fi
    fi
fi

say "===== SUMMARY ====="
say "phase1=$PHASE1_VERDICT phase2=$PHASE2_VERDICT log=$LOG"

if [ "$JSON" -eq 1 ]; then
    printf '{"kb":"KB-ATBOOT","sample":"%s","phase1":"%s","phase2":"%s","log":"%s"}\n' \
        "$(basename "$SAMPLE")" "$PHASE1_VERDICT" "$PHASE2_VERDICT" "$LOG"
else
    echo "===== KB-ATBOOT reproduce summary ====="
    echo "phase1 (no skill): $PHASE1_VERDICT"
    echo "phase2 (with skill): $PHASE2_VERDICT"
    echo "full log: $LOG"
fi

# 判定：两阶段分别符合预期才整体 PASS
if [ "$PHASE1_VERDICT" = "reproduced" ] && [ "$PHASE2_VERDICT" = "fixed" ]; then
    exit 0
fi
exit 1
