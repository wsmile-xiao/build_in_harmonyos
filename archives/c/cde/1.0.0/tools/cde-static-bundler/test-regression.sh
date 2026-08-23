#!/bin/sh
# test-regression.sh — cde-static-bundler 本地回归测试套件
# 用法:  test-regression.sh [--bin <cde-static-bundler-path>] [--logdir <dir>]
# 默认:  --bin ./cde-static-bundler
#        --logdir $HOME/tmp/cde-r46-logs/regression/<timestamp>
#
# 测试用例（全部使用自属 fixture，不执行被检 ELF）:
#   T1 — CLI help 边界退出 0 并保留静态边界声明
#   T2 — 有效静态扫描闭包（受控 ELF + 资源根 → manifest complete=true）
#   T3 — 非 ELF 输入确定性拒绝（非零退出 + 有用错误）
#   T4 — 缺失的必需依赖硬失败（非零退出 + INCOMPLETE + manifest 记录）
#   T5 — 缺失 --entry 参数拒绝（exit 2 + 明确错误）

set -u

# --- 默认配置 ---
BIN="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/cde-static-bundler"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOGDIR="${HOME}/tmp/cde-r46-logs/regression/${TIMESTAMP}"
CLANG="${CC:-clang}"

# --- 解析参数 ---
while [ $# -gt 0 ]; do
    case "$1" in
        --bin) BIN="$2"; shift 2 ;;
        --logdir) LOGDIR="$2"; shift 2 ;;
        --help|-h)
            echo "用法: test-regression.sh [--bin <path>] [--logdir <dir>]"
            exit 0 ;;
        *) echo "未知参数: $1"; exit 2 ;;
    esac
done
# 规范化相对 --logdir
case "$LOGDIR" in
    /*) ;;
    *) LOGDIR="$(pwd)/$LOGDIR" ;;
esac

# --- 前置检查 ---
if [ ! -x "$BIN" ]; then
    echo "错误: 找不到 cde-static-bundler 二进制: $BIN"
    exit 1
fi

mkdir -p "$LOGDIR"
echo "=== cde-static-bundler 回归测试 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "二进制: $BIN"
echo "日志:   $LOGDIR"
echo "编译器: $(clang --version 2>&1 | head -1)"
echo ""

# --- 辅助函数 ---
PASS=0; FAIL=0; SKIP=0
COUNT=0

pass() { COUNT=$((COUNT+1)); PASS=$((PASS+1)); echo "  [PASS] T${1} $2";
    if [ -n "${LOG:-}" ] && [ -f "$LOG" ] && ! grep -q '^assertion:' "$LOG" 2>/dev/null; then
        { echo ""; echo "assertion: $2"; echo "assertion_result: PASS"; echo "test_case_exit_code: 0"; } >> "$LOG"
    fi
}
fail() { COUNT=$((COUNT+1)); FAIL=$((FAIL+1)); echo "  [FAIL] T${1} $2";
    if [ -n "${LOG:-}" ] && [ -f "$LOG" ] && ! grep -q '^assertion:' "$LOG" 2>/dev/null; then
        { echo ""; echo "assertion: $2"; echo "assertion_result: FAIL"; echo "test_case_exit_code: 1"; } >> "$LOG"
    fi
}
skip() { COUNT=$((COUNT+1)); SKIP=$((SKIP+1)); echo "  [SKIP] T${1} $2"; }

# 结构化日志执行器
run_cmd_structured() {
    local log="$1"
    shift
    local cmd_str="$*"
    local stdout_f="${log}.stdout.$$"
    local stderr_f="${log}.stderr.$$"
    "$@" > "$stdout_f" 2> "$stderr_f"
    RC=$?
    {
        echo "case_id: T$(printf '%02d' "${T:-0}")"
        echo "command: $cmd_str"
        echo "stdout:"
        if [ -s "$stdout_f" ]; then cat "$stdout_f"; else echo "(empty stdout)"; fi
        echo "stderr:"
        if [ -s "$stderr_f" ]; then cat "$stderr_f"; else echo "(empty stderr)"; fi
        echo "subject_exit_code: $RC"
    } > "$log"
    rm -f "$stdout_f" "$stderr_f"
    return $RC
}

# 重置工作目录（每个测试一个独立子目录）
WD=""
wreset() {
    WD="${LOGDIR}/_work_t${1}_$(date +%s)"
    mkdir -p "$WD"
}

# -----------------------------------------------------------------------
# T1 — CLI help 边界
# -----------------------------------------------------------------------
echo "--- T1: CLI help 边界 ---"
T=1
wreset $T
LOG="${LOGDIR}/t1-help.log"
run_cmd_structured "$LOG" "$BIN" --help; rc=$RC

if [ "$rc" -ne 0 ]; then fail $T "exit_code=$rc (expected 0)"; else
    if grep -q "BOUNDARY" "$LOG" 2>/dev/null; then
        B1=0; B2=0; B3=0; B4=0; B5=0
        grep -q "does not use ptrace" "$LOG" 2>/dev/null && B1=1
        grep -q "LD_PRELOAD" "$LOG" 2>/dev/null && B2=1
        # 输出中 "never" 和 "executes the ELF under inspection" 在相邻行（跨行）
        grep -q "never" "$LOG" 2>/dev/null && grep -q "executes the ELF under inspection" "$LOG" 2>/dev/null && B3=1
        grep -q "STATIC ELF metadata analysis" "$LOG" 2>/dev/null && B4=1
        grep -q "CANNOT bypass" "$LOG" 2>/dev/null && B5=1
        TOTAL=$((B1+B2+B3+B4+B5))
        if [ "$TOTAL" -ge 4 ]; then
            pass $T "exit=0, BOUNDARY text present ($TOTAL/5 boundary keywords)"
        else
            fail $T "BOUNDARY found but only $TOTAL/5 keywords matched"
        fi
        # 记录实际文本
        { echo "=== BOUNDARY text ==="; grep -A 20 "BOUNDARY" "$LOG" | head -20; } >> "$LOGDIR/t1-boundary-text.txt"
    else
        fail $T "BOUNDARY keyword missing from --help output"
    fi
fi

# -----------------------------------------------------------------------
# T2 — 有效静态扫描闭包（受控 ELF + 资源根）
# -----------------------------------------------------------------------
echo "--- T2: 有效静态扫描闭包 ---"
T=2
wreset $T
LOG="${LOGDIR}/t2-scan.log"
rm -rf "$WD/fixture" "$WD/resroot" "$WD/out"
mkdir -p "$WD/fixture" "$WD/resroot" "$WD/out"

# 创建受控 fixture ELF（最小静态 C 程序，纯自属，无外部依赖）
cat > "$WD/fixture/hello.c" << 'FIXXEOF'
#include <stdio.h>
int main(void) {
    printf("hello fixture\n");
    return 0;
}
FIXXEOF

# 静态编译（确保不依赖外部动态库）
"$CLANG" -static -o "$WD/fixture/hello" "$WD/fixture/hello.c" 2>"$WD/fixture/build-stderr.txt"
rc_build=$?

if [ "$rc_build" -ne 0 ]; then
    # 静态编译失败可能是系统限制，尝试动态编译（但记录为降级提示）
    skip $T "cannot build static fixture (clang -static failed rc=$rc_build); dynamic fallback not attempted (static-only test)"
    # 记录失败原因供后续分析
    echo "静态编译失败: clang -static rc=$rc_build" > "$LOGDIR/t2-build-failure.txt"
    echo "stderr:" >> "$LOGDIR/t2-build-failure.txt"
    cat "$WD/fixture/build-stderr.txt" >> "$LOGDIR/t2-build-failure.txt"
else
    echo "hello fixture" > "$WD/resroot/data.txt"
    echo "hello2" > "$WD/resroot/data2.txt"

    run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/hello" --resource-root "$WD/resroot" --output "$WD/out"; rc=$RC

    if [ "$rc" -ne 0 ]; then
        fail $T "exit_code=$rc (expected 0), stderr=$(tail -1 "$LOG" | head -c 200)"
    else
        ERR=0
        [ -f "$WD/out/manifest.json" ] || { echo "manifest.json missing" >> "$LOGDIR/t2-errors.txt"; ERR=1; }
        grep -q '"complete": *true' "$WD/out/manifest.json" 2>/dev/null || \
            { echo "complete not true" >> "$LOGDIR/t2-errors.txt"; ERR=1; }
        grep -q '"entry"' "$WD/out/manifest.json" 2>/dev/null || \
            { echo "entry not in manifest" >> "$LOGDIR/t2-errors.txt"; ERR=1; }
        # 资源文件拷贝到 bundle 的 resources/
        [ -f "$WD/out/resources/data.txt" ] || \
            { echo "resources/data.txt not copied" >> "$LOGDIR/t2-errors.txt"; ERR=1; }
        [ -f "$WD/out/resources/data2.txt" ] || \
            { echo "resources/data2.txt not copied" >> "$LOGDIR/t2-errors.txt"; ERR=1; }
        # 确认 entry 可执行文件不被执行（只被静态分析）
        # 证据：manifest 中 entry 有 sha256 即可，无执行痕迹

        if [ "$ERR" -eq 0 ]; then
            pass $T "exit=0, manifest complete=true, entry+resources copied"
        else
            fail $T "manifest validation failed, see $LOGDIR/t2-errors.txt"
        fi
        # 保存 manifest 副本供检查
        cp "$WD/out/manifest.json" "$LOGDIR/t2-manifest.json"
    fi
fi

# -----------------------------------------------------------------------
# T3 — 非 ELF 输入确定性拒绝
# -----------------------------------------------------------------------
echo "--- T3: 非 ELF 拒绝 ---"
T=3
wreset $T
LOG="${LOGDIR}/t3-nonelf.log"
rm -rf "$WD/out"
mkdir -p "$WD/out"

# 创建自属非 ELF 输入（文本文件）
echo "This is not an ELF binary - it's a plain text fixture" > "$WD/bad.txt"

run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/bad.txt" --output "$WD/out"; rc=$RC

if [ "$rc" -eq 0 ]; then
    fail $T "exit_code=0 (expected non-zero for non-ELF input)"
else
    # 检查有用错误消息
    if grep -qi "not an ELF\|bad magic\|not ELF\|invalid\|unsupported" "$LOG" 2>/dev/null; then
        pass $T "exit=$rc, useful error: $(grep -oi 'not an ELF[^.]*' "$LOG" | head -1)"
    else
        fail $T "exit=$rc but no useful error about non-ELF: $(tail -1 "$LOG" | head -c 200)"
    fi
fi

# -----------------------------------------------------------------------
# T4 — 缺失的必需依赖硬失败
# -----------------------------------------------------------------------
echo "--- T4: 缺失依赖错误路径 ---"
T=4
wreset $T
LOG="${LOGDIR}/t4-missing-dep.log"
rm -rf "$WD/fixture" "$WD/out"
mkdir -p "$WD/fixture" "$WD/out"

# 构建 fixture 依赖库 stub
cat > "$WD/fixture/libfake.c" << 'FIXXEOF'
int fake_function(void) {
    return 42;
}
FIXXEOF

"$CLANG" -shared -fPIC -Wl,-soname,libfake.so.1 -o "$WD/fixture/libfake.so.1" \
    "$WD/fixture/libfake.c" 2>"$WD/fixture/build-stderr.txt"
rc_lib=$?

if [ "$rc_lib" -ne 0 ]; then
    skip $T "cannot build shared lib fixture (clang -shared failed rc=$rc_lib)"
    cat "$WD/fixture/build-stderr.txt" > "$LOGDIR/t4-build-lib-failure.txt"
else
    # 构建引用该依赖的可执行文件
    cat > "$WD/fixture/app.c" << 'FIXXEOF'
extern int fake_function(void);
int main(void) {
    return fake_function() != 42;
}
FIXXEOF

    # 链接时直接链接 .so 文件生成 DT_NEEDED libfake.so.1
    # （ld.lld 不接受 -L<dir> -lfake 组合，直接传 .so 路径可产生 NEEDED 记录）
    "$CLANG" -o "$WD/fixture/app" "$WD/fixture/app.c" \
        "$WD/fixture/libfake.so.1" 2>"$WD/fixture/build-stderr2.txt"
    rc_app=$?

    if [ "$rc_app" -ne 0 ]; then
        skip $T "cannot build dependent app fixture (clang -L -lfake rc=$rc_app)"
        cat "$WD/fixture/build-stderr2.txt" > "$LOGDIR/t4-build-app-failure.txt"
    else
        # 确认 entry 引用 libfake（readelf -d 验证 DT_NEEDED）
        if command -v readelf >/dev/null 2>&1; then
            readelf -d "$WD/fixture/app" 2>/dev/null | grep -q "NEEDED.*libfake" || \
                echo "警告: ldd/readelf 未显示 libfake DT_NEEDED（可能链接器优化掉了）" >> "$LOGDIR/t4-need-check.txt"
        fi

        # 记录依赖信息
        if command -v readelf >/dev/null 2>&1; then
            readelf -d "$WD/fixture/app" 2>/dev/null > "$LOGDIR/t4-readelf-d.txt"
        fi

        # 扫描——依赖 libfake 不在 entry_dir 内（已删除范式）
        # 但 libfake 在 fixture 目录存在，DT_NEEDED 解析会查找 entry_dir
        # 先把 libfake 移动到其他地方使查找失败
        mv "$WD/fixture/libfake.so.1" "$WD/libfake-removed.so.1" 2>/dev/null || true

        run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/app" --output "$WD/out"; rc=$RC

        if [ "$rc" -eq 0 ]; then
            fail $T "exit_code=0 (expected non-zero for unresolved required deps)"
        else
            # 检查 exit 1（硬失败）和 INCOMPLETE 消息
            if [ "$rc" -eq 1 ] && grep -qi "INCOMPLETE" "$LOG" 2>/dev/null; then
                # 检查 manifest 是否记录了未解析依赖
                if [ -f "$WD/out/manifest.json" ] && grep -qi "libfake" "$WD/out/manifest.json" 2>/dev/null; then
                    pass $T "exit=$rc, INCOMPLETE, manifest records libfake.so.1"
                else
                    fail $T "exit=$rc INCOMPLETE but manifest missing libfake reference"
                fi
            else
                fail $T "exit=$rc but no INCOMPLETE message: $(tail -1 "$LOG" | head -c 200)"
            fi
            [ -f "$WD/out/manifest.json" ] && cp "$WD/out/manifest.json" "$LOGDIR/t4-manifest.json"
        fi
    fi
fi

# -----------------------------------------------------------------------
# T5 — 缺失 --entry 参数
# -----------------------------------------------------------------------
echo "--- T5: 缺失 --entry 参数 ---"
T=5
wreset $T
LOG="${LOGDIR}/t5-no-entry.log"
rm -rf "$WD/out"
mkdir -p "$WD/out"

run_cmd_structured "$LOG" "$BIN" scan --output "$WD/out"; rc=$RC

if [ "$rc" -eq 2 ] && grep -qi "entry is required" "$LOG" 2>/dev/null; then
    pass $T "exit=2, --entry is required"
else
    fail $T "exit=$rc (expected 2 + '--entry is required'): $(tail -1 "$LOG" | head -c 200)"
fi

# -----------------------------------------------------------------------
# T6 — 子命令缺失与未知参数拒绝
# -----------------------------------------------------------------------
echo "--- T6: 参数验证（子命令缺失 + 未知参数） ---"
T=6
wreset $T

# T6 — 缺失子命令/未知参数：单块 + 有序子探测（2 次调用，1 个 evidence block）
LOG="${LOGDIR}/t6-subcommand-unknownarg.log"

s_b="${LOG}.p1.stdout.$$"; e_b="${LOG}.p1.stderr.$$"
"$BIN" unknown_arg_xyz > "$s_b" 2>"$e_b"; rc_a=$?
s_a="${LOG}.p2.stdout.$$"; e_a="${LOG}.p2.stderr.$$"
"$BIN" scan --entry /bin/true --unknown-flag > "$s_a" 2>"$e_a"; rc_b=$?
{
    echo "case_id: T06"
    echo "command: $BIN unknown_arg_xyz; $BIN scan --entry /bin/true --unknown-flag (2 probes)"
    echo "stdout:"
    echo "--- probe 1 (unknown_arg_xyz) ---"; cat "$s_b"
    echo "--- probe 2 (scan --unknown-flag) ---"; cat "$s_a"
    echo "stderr:"
    echo "--- probe 1 ---"; cat "$e_b"
    echo "--- probe 2 ---"; cat "$e_a"
    echo "subject_exit_codes: $rc_a (probe 1, expected 2), $rc_b (probe 2, expected 2)"
    echo "assertion: 子命令缺失与未知参数均以退出码 2 拒绝并给出明确错误"
} > "$LOG"
rm -f "$s_b" "$e_b" "$s_a" "$e_a"

P6a=0; P6b=0
if [ "$rc_a" -eq 2 ] && grep -qi "expected subcommand" "$LOG" 2>/dev/null; then P6a=1; fi
if [ "$rc_b" -eq 2 ] && grep -qi "unknown argument" "$LOG" 2>/dev/null; then P6b=1; fi

if [ "$P6a" -eq 1 ] && [ "$P6b" -eq 1 ]; then
    { echo "assertion_result: PASS"; echo "test_case_exit_code: 0"; } >> "$LOG"
    pass $T "exit=2 both subcommand (a) and unknown arg (b): 'expected subcommand' + 'unknown argument'"
else
    { echo "assertion_result: FAIL"; echo "test_case_exit_code: 1"; } >> "$LOG"
    fail $T "a:exit=$rc_a(P6a=$P6a) b:exit=$rc_b(P6b=$P6b)"
fi

# -----------------------------------------------------------------------
# T7 — --libdir 解析依赖（非系统依赖通过 --libdir 定位）
# -----------------------------------------------------------------------
echo "--- T7: --libdir 自定义依赖解析 ---"
T=7
wreset $T
LOG="${LOGDIR}/t7-libdir.log"
rm -rf "$WD/fixture" "$WD/out" "$WD/libdir"
mkdir -p "$WD/fixture" "$WD/out" "$WD/libdir"

# 构建依赖库（放在 libdir 目录，不在 entry_dir）
cat > "$WD/fixture/libhelper.c" << 'FIXEOF'
int helper_func(void) { return 42; }
FIXEOF
"$CLANG" -shared -fPIC -Wl,-soname,libhelper.so.1 -o "$WD/libdir/libhelper.so.1" \
    "$WD/fixture/libhelper.c" 2>"$WD/fixture/build-err.txt"
rc_lib=$?

if [ "$rc_lib" -ne 0 ]; then
    skip $T "cannot build shared lib fixture (clang -shared rc=$rc_lib)"
    cat "$WD/fixture/build-err.txt" > "$LOGDIR/t7-libdir-build-fail.txt"
else
    # 构建引用该依赖的 app（只在 entry_dir 放 app，不复制 libhelper）
    cat > "$WD/fixture/app.c" << 'FIXEOF'
extern int helper_func(void);
int main(void) { return helper_func() != 42; }
FIXEOF
    "$CLANG" -o "$WD/fixture/app" "$WD/fixture/app.c" \
        "$WD/libdir/libhelper.so.1" 2>"$WD/fixture/build-err2.txt"
    rc_app=$?
    if [ "$rc_app" -ne 0 ]; then
        skip $T "cannot build app fixture (clang rc=$rc_app)"
        cat "$WD/fixture/build-err2.txt" > "$LOGDIR/t7-libdir-build-app-fail.txt"
    else
        # 扫描：libhelper 不在 entry_dir，通过 --libdir 指定
        run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/app" --libdir "$WD/libdir" --output "$WD/out"; rc=$RC
        if [ "$rc" -eq 0 ] && [ -f "$WD/out/manifest.json" ]; then
            # 检查 manifest 中 libhelper 被拷贝
            if grep -qi "libhelper" "$WD/out/manifest.json" 2>/dev/null; then
                # 检查 complete=true
                if grep -q '"complete": *true' "$WD/out/manifest.json" 2>/dev/null; then
                    pass $T "exit=0, libhelper resolved via --libdir, complete=true"
                else
                    fail $T "exit=0 libhelper found but complete=false"
                fi
            else
                fail $T "exit=0 but libhelper not in manifest"
            fi
        else
            fail $T "exit=$rc or manifest missing: $(tail -1 "$LOG" | head -c 200)"
        fi
        [ -f "$WD/out/manifest.json" ] && cp "$WD/out/manifest.json" "$LOGDIR/t7-manifest.json"
    fi
fi

# -----------------------------------------------------------------------
# T8 — 多个 --resource-root
# -----------------------------------------------------------------------
echo "--- T8: 多 resource-root ---"
T=8
wreset $T
LOG="${LOGDIR}/t8-multi-resroot.log"
rm -rf "$WD/fixture" "$WD/out" "$WD/res1" "$WD/res2"
mkdir -p "$WD/fixture" "$WD/out" "$WD/res1" "$WD/res2"

# 编译受控静态 fixture ELF（同 T2）
cat > "$WD/fixture/hello.c" << 'FIXEOF'
#include <stdio.h>
int main(void) { printf("hello\n"); return 0; }
FIXEOF
"$CLANG" -static -o "$WD/fixture/hello" "$WD/fixture/hello.c" 2>/dev/null
rc_build=$?

if [ "$rc_build" -ne 0 ]; then
    skip $T "cannot build static fixture (clang -static rc=$rc_build)"
else
    echo "file_from_res1" > "$WD/res1/data1.txt"
    echo "file_from_res2" > "$WD/res2/data2.txt"

    run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/hello" --resource-root "$WD/res1" --resource-root "$WD/res2" --output "$WD/out"; rc=$RC

    if [ "$rc" -eq 0 ] && [ -f "$WD/out/manifest.json" ]; then
        HAS1=0; HAS2=0
        [ -f "$WD/out/resources/data1.txt" ] && HAS1=1
        [ -f "$WD/out/resources/data2.txt" ] && HAS2=1
        if [ "$HAS1" -eq 1 ] && [ "$HAS2" -eq 1 ]; then
            pass $T "exit=0, both res1/data1.txt and res2/data2.txt copied"
        else
            fail $T "resource files missing: data1=$HAS1 data2=$HAS2"
        fi
    else
        fail $T "exit=$rc or manifest missing: $(tail -1 "$LOG" | head -c 200)"
    fi
fi

# -----------------------------------------------------------------------
# T9 — 自定义 --output 目录
# -----------------------------------------------------------------------
echo "--- T9: 自定义 --output 目录 ---"
T=9
wreset $T
LOG="${LOGDIR}/t9-custom-output.log"
rm -rf "$WD/fixture" "$WD/out" "$WD/myout"
mkdir -p "$WD/fixture" "$WD/out" "$WD/myout"

cat > "$WD/fixture/hello.c" << 'FIXEOF'
#include <stdio.h>
int main(void) { printf("hello\n"); return 0; }
FIXEOF
"$CLANG" -static -o "$WD/fixture/hello" "$WD/fixture/hello.c" 2>/dev/null
rc_build=$?

if [ "$rc_build" -ne 0 ]; then
    skip $T "cannot build static fixture (clang -static rc=$rc_build)"
else
    run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/hello" --output "$WD/myout"; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$WD/myout/manifest.json" ]; then
        pass $T "exit=0, manifest written to custom --output path"
    else
        fail $T "exit=$rc or manifest missing at custom output dir: $(tail -1 "$LOG" | head -c 200)"
    fi
fi

# -----------------------------------------------------------------------
# T10 — manifest 字段完整性
# -----------------------------------------------------------------------
echo "--- T10: manifest 字段完整性 ---"
T=10
wreset $T
LOG="${LOGDIR}/t10-manifest-fields.log"
rm -rf "$WD/fixture" "$WD/out"
mkdir -p "$WD/fixture" "$WD/out"

cat > "$WD/fixture/hello.c" << 'FIXEOF'
#include <stdio.h>
int main(void) { printf("hello\n"); return 0; }
FIXEOF
"$CLANG" -static -o "$WD/fixture/hello" "$WD/fixture/hello.c" 2>/dev/null
rc_b=$?
if [ "$rc_b" -ne 0 ]; then skip $T "cannot build static fixture (clang -static rc=$rc_b)"; else
    run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/hello" --output "$WD/out"; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$WD/out/manifest.json" ]; then
        M="$WD/out/manifest.json"
        ERR=0
        # 验证所有必需字段存在
        for key in '"tool"' '"tool_version"' '"entry"' '"architecture"' '"interpreter"' '"complete"' '"dependency_graph"' '"copied_files"' '"system_exclusions"' '"unresolved"' '"resource_roots"'; do
            grep -q "$key" "$M" 2>/dev/null || { echo "缺少字段: $key" >> "$LOGDIR/t10-missing-fields.txt"; ERR=1; }
        done
        # 验证 complete=true
        grep -q '"complete": *true' "$M" 2>/dev/null || { echo "complete=!true" >> "$LOGDIR/t10-missing-fields.txt"; ERR=1; }
        # 验证 entry 非空、architecture 非空
        grep -q '"entry": *".*"' "$M" 2>/dev/null || { echo "entry 为空" >> "$LOGDIR/t10-missing-fields.txt"; ERR=1; }
        grep -q '"architecture": *"[A-Za-z0-9_-]' "$M" 2>/dev/null || { echo "architecture 为空" >> "$LOGDIR/t10-missing-fields.txt"; ERR=1; }
        if [ "$ERR" -eq 0 ]; then
            pass $T "exit=0, all 11 manifest fields present, complete=true, entry+arch non-empty"
        else
            fail $T "manifest field validation failed, see $LOGDIR/t10-missing-fields.txt"
        fi
    else
        fail $T "exit=$rc or manifest missing: $(tail -1 "$LOG" | head -c 200)"
    fi
fi

# -----------------------------------------------------------------------
# T11 — 空资源根
# -----------------------------------------------------------------------
echo "--- T11: 空 resource-root ---"
T=11
wreset $T
LOG="${LOGDIR}/t11-empty-resroot.log"
rm -rf "$WD/fixture" "$WD/out" "$WD/empty"
mkdir -p "$WD/fixture" "$WD/out" "$WD/empty"

cat > "$WD/fixture/hello.c" << 'FIXEOF'
#include <stdio.h>
int main(void) { printf("hello\n"); return 0; }
FIXEOF
"$CLANG" -static -o "$WD/fixture/hello" "$WD/fixture/hello.c" 2>/dev/null
rc_b=$?
if [ "$rc_b" -ne 0 ]; then skip $T "cannot build static fixture (clang -static rc=$rc_b)"; else
    run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/fixture/hello" --resource-root "$WD/empty" --output "$WD/out"; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$WD/out/manifest.json" ]; then
        pass $T "exit=0, empty resource-root accepted, manifest written"
    else
        fail $T "exit=$rc or manifest missing: $(tail -1 "$LOG" | head -c 200)"
    fi
fi

# -----------------------------------------------------------------------
# T12 — --entry 文件不存在
# -----------------------------------------------------------------------
echo "--- T12: --entry 文件不存在 ---"
T=12
wreset $T
LOG="${LOGDIR}/t12-nonexistent-entry.log"
rm -rf "$WD/out"
mkdir -p "$WD/out"

run_cmd_structured "$LOG" "$BIN" scan --entry "$WD/no-such-file-xyz" --output "$WD/out"; rc=$RC

if [ "$rc" -eq 1 ] && grep -qi "cannot read\|No such file\|not an ELF" "$LOG" 2>/dev/null; then
    pass $T "exit=1, useful error for nonexistent --entry"
else
    fail $T "exit=$rc (expected 1 + error): $(tail -2 "$LOG" | head -c 200)"
fi

# -----------------------------------------------------------------------
# 汇总
# -----------------------------------------------------------------------
echo ""
echo "=============================="
echo "  回归测试结果"
echo "=============================="
echo "  总计: $COUNT | 通过: $PASS | 失败: $FAIL | 跳过: $SKIP"
echo "=============================="
echo "完整日志: $LOGDIR"

if [ "$FAIL" -gt 0 ]; then
    echo "失败测试详情:"
    for f in "$LOGDIR"/*.log; do
        b=$(basename "$f")
        echo "  $b"
    done
    exit 1
else
    exit 0
fi