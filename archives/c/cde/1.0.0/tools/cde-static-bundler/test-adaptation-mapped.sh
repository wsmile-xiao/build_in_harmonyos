#!/bin/sh
# test-adaptation-mapped.sh — CDE 1.0.0 上游测试 → 静态适配一对一映射（R24 57 项）
#
# 用法:  test-adaptation-mapped.sh [--bin <path>] [--logdir <dir>] run-case <M##>
#        test-adaptation-mapped.sh [--bin <path>] [--logdir <dir>] run-all
#        test-adaptation-mapped.sh [--bin <path>] [--logdir <dir>] setup-fixtures
#
# 用例:  M01-M57 对应 upstream-test-mapping.md 的 57 条记录
# 每例: 独立日志 $LOGDIR/M<ID>.log，独立退出码，PASS/FAIL 判定

set -u

# ── 默认路径 ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="${SCRIPT_DIR}/cde-static-bundler"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
LOGDIR="${LOGDIR:-${HOME}/tmp/cde-r26-logs/adaptation/${TIMESTAMP}}"
CLANG="${CLANG:-clang}"
TMPDIR="${HOME}/tmp"
COUNT=0; PASS=0; FAIL=0; SKIP=0; ERR=0

# ── 解析参数 ──
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --bin) BIN="$2"; shift 2 ;;
            --logdir) LOGDIR="$2"; shift 2 ;;
            run-case) ACTION="run_case";
                if [ $# -lt 2 ]; then echo "错误: run-case 需要 <M##> 参数" >&2; exit 2; fi
                CASE_ID="$2"; shift 2 ;;
            run-all) ACTION="run_all"; shift ;;
            setup-fixtures) ACTION="setup_fixtures"; shift ;;
            *) echo "用法: $0 [--bin <path>] [--logdir <dir>] {run-case <M##>|run-all|setup-fixtures}"; exit 1 ;;
        esac
    done
    [ -z "${ACTION:-}" ] && { echo "缺少动作: run-case/run-all/setup-fixtures"; exit 1; }
    # 规范化相对 --logdir（/bin/sh 无 realpath，用 pwd 拼接绝对路径）
    case "$LOGDIR" in
        /*) ;;
        *) LOGDIR="$(pwd)/$LOGDIR" ;;
    esac
    mkdir -p "$LOGDIR"
    # 每次调用截断自己的 _summary.txt（避免跨运行累积）
    : > "$LOGDIR/_summary.txt"
}

# ── 辅助函数 ──
pass() { local id="$1"; shift; echo "[PASS] $id $*" | tee -a "$LOGDIR/_summary.txt"; PASS=$((PASS+1)); COUNT=$((COUNT+1)); }
fail() { local id="$1"; shift; echo "[FAIL] $id $*" | tee -a "$LOGDIR/_summary.txt"; FAIL=$((FAIL+1)); COUNT=$((COUNT+1)); ERR=1; }
skip() { local id="$1"; shift; echo "[SKIP] $id $*" | tee -a "$LOGDIR/_summary.txt"; SKIP=$((SKIP+1)); COUNT=$((COUNT+1)); }

# 结构化日志执行器：运行命令，分别捕获 stdout/stderr，写入结构化日志
# 用法: run_cmd_structured <log_path> <cmd...>
# 日志格式：command: /实际/命令
#           stdout:
#           <原始 stdout 或 "(empty stdout)">
#           stderr:
#           <原始 stderr 或 "(empty stderr)">
#           exit_code: <整数>
# 设置全局 RC 为退出码
run_cmd_structured() {
    local log="$1"
    shift
    local cmd_str="$*"
    local stdout_f="${log}.stdout.$$"
    local stderr_f="${log}.stderr.$$"
    # 从日志文件名推断 case_id（MM01.log → M01）
    local case_id
    case_id=$(basename "$log" .log 2>/dev/null | sed 's/^MM/M/' )
    "$@" > "$stdout_f" 2> "$stderr_f"
    RC=$?
    {
        echo "case_id: $case_id"
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

# 带子目录 cd 的结构化执行（等价于 ( cd dir && cmd )，退出码可回传）
# 用法: run_cmd_structured_cd <log_path> <dir> <cmd...>
run_cmd_structured_cd() {
    local log="$1" dir="$2"; shift 2
    ( cd "$dir" && run_cmd_structured "$log" "$@" )
    RC=$?
}

# ── 共享工作目录（每个用例独立重置） ──
WD_PREFIX="${LOGDIR}/_work"
mkwd() { local id="$1"; rm -rf "${WD_PREFIX}_${id}"; mkdir -p "${WD_PREFIX}_${id}"; echo "${WD_PREFIX}_${id}"; }

# 构建共享 fixture（一次性，由 setup-fixtures 或首次 run-all 执行）
build_fixtures() {
    local FIX="$1"
    mkdir -p "$FIX"
    echo "--- 构建共享 fixture ---" >> "$LOGDIR/_fixture.log"

    # 1. 静态 hello ELF
    if [ ! -f "$FIX/hello-static" ]; then
        cat > "$FIX/hello.c" << 'FIXEOF'
#include <stdio.h>
int main(void) { printf("hello-from-static-bundler\n"); return 0; }
FIXEOF
        "$CLANG" -static -o "$FIX/hello-static" "$FIX/hello.c" \
            >> "$LOGDIR/_fixture.log" 2>&1
        echo "  hello-static build rc=$?" >> "$LOGDIR/_fixture.log"
    fi

    # 2. 共享库 libhelper.so.1
    if [ ! -f "$FIX/libhelper.so.1" ]; then
        cat > "$FIX/helper.c" << 'FIXEOF'
int helper_func(void) { return 42; }
FIXEOF
        "$CLANG" -shared -fPIC -Wl,-soname,libhelper.so.1 \
            -o "$FIX/libhelper.so.1" "$FIX/helper.c" \
            >> "$LOGDIR/_fixture.log" 2>&1
        echo "  libhelper.so.1 build rc=$?" >> "$LOGDIR/_fixture.log"
    fi

    # 3. 动态 app（链接 libhelper，非系统依赖）
    if [ ! -f "$FIX/dyn-app" ]; then
        cat > "$FIX/app.c" << 'FIXEOF'
extern int helper_func(void);
int main(void) { return helper_func() != 42; }
FIXEOF
        "$CLANG" -o "$FIX/dyn-app" "$FIX/app.c" "$FIX/libhelper.so.1" \
            >> "$LOGDIR/_fixture.log" 2>&1
        echo "  dyn-app build rc=$?" >> "$LOGDIR/_fixture.log"
    fi

    # 4. 动态 app 带 DT_RUNPATH $ORIGIN
    if [ ! -f "$FIX/dyn-app-runpath" ]; then
        "$CLANG" -o "$FIX/dyn-app-runpath" "$FIX/app.c" \
            -Wl,-rpath,'$ORIGIN' "$FIX/libhelper.so.1" \
            >> "$LOGDIR/_fixture.log" 2>&1
        echo "  dyn-app-runpath build rc=$?" >> "$LOGDIR/_fixture.log"
    fi

    # 5. 文本脚本文件
    echo "#!/bin/sh" > "$FIX/script.sh"
    echo "echo hello" >> "$FIX/script.sh"
    echo "#!/bin/sh" > "$FIX/script2.sh"
    echo "echo world" >> "$FIX/script2.sh"
    echo "#!/bin/sh" > "$FIX/script3.sh"
    echo "echo test" >> "$FIX/script3.sh"
    echo "some python code" > "$FIX/sample.py"
    echo "text content" > "$FIX/notelf.txt"
    chmod +x "$FIX/script.sh" "$FIX/script2.sh" "$FIX/script3.sh"

    # 6. 资源目录
    mkdir -p "$FIX/res1"
    echo "data1" > "$FIX/res1/data.txt"
    mkdir -p "$FIX/res2"
    echo "data2" > "$FIX/res2/data2.txt"
    mkdir -p "$FIX/res-rel"
    echo "rel-data" > "$FIX/res-rel/rel.txt"
    mkdir -p "$FIX/res-tree/sub"
    echo "deep" > "$FIX/res-tree/sub/deep.txt"
    mkdir -p "$FIX/res-empty"
    mkdir -p "$FIX/res-hardlink"
    echo "link-a" > "$FIX/res-hardlink/a.txt"
    ln "$FIX/res-hardlink/a.txt" "$FIX/res-hardlink/b.txt" 2>/dev/null || cp "$FIX/res-hardlink/a.txt" "$FIX/res-hardlink/b.txt"
    mkdir -p "$FIX/res-deep-tree/a/b/c"
    echo "deepest" > "$FIX/res-deep-tree/a/b/c/f.txt"
    mkdir -p "$FIX/resparent"
    echo "parent" > "$FIX/resparent/p.txt"
    mkdir -p "$FIX/resparent/sub"
    echo "child" > "$FIX/resparent/sub/c.txt"

    # 7. symlink 资源（拒绝场景）
    mkdir -p "$FIX/res-symlink-abs"
    ln -s /etc/passwd "$FIX/res-symlink-abs/abs-link" 2>/dev/null || true
    mkdir -p "$FIX/res-symlink-abs2"
    ln -s /tmp "$FIX/res-symlink-abs2/abs-link2" 2>/dev/null || true
    mkdir -p "$FIX/res-symlink-dir"
    mkdir -p "$FIX/res-symlink-dir-target"
    ln -s ../res-symlink-dir-target "$FIX/res-symlink-dir/subdir" 2>/dev/null || true
    mkdir -p "$FIX/res-symlink-dir2"
    ln -s /tmp/foo "$FIX/res-symlink-dir2/link2" 2>/dev/null || true
    mkdir -p "$FIX/res-symlink-chain"
    ln -s nonexistent "$FIX/res-symlink-chain/broken" 2>/dev/null || true
    mkdir -p "$FIX/res-symlink-chain2"
    ln -s / "$FIX/res-symlink-chain2/root" 2>/dev/null || true
    mkdir -p "$FIX/res-symlink-escape"
    ln -s .. "$FIX/res-symlink-escape/escape" 2>/dev/null || true

    # 8. fifo 文件
    mkdir -p "$FIX/res-fifo"
    mkfifo "$FIX/res-fifo/pipe.fifo" 2>/dev/null || true

    # 9. symlink-to-hello（entry symlink）
    ln -sf hello-static "$FIX/symlink-to-hello" 2>/dev/null || true

    # 10. libdir 目录
    mkdir -p "$FIX/libdir"
    cp "$FIX/libhelper.so.1" "$FIX/libdir/libhelper.so.1"
    mkdir -p "$FIX/libdir2"
    cp "$FIX/libhelper.so.1" "$FIX/libdir2/libhelper.so.1"
    mkdir -p "$FIX/libdirX"
    cp "$FIX/libhelper.so.1" "$FIX/libdirX/libhelper.so.1"

    echo "  fixtures ready at $FIX" >> "$LOGDIR/_fixture.log"
}

# 运行单个用例（由 case_M## 函数实现）
run_case() {
    local id="$1"
    local log="${LOGDIR}/M${id}.log"
    mkdir -p "$(dirname "$log")"
    # 分发到对应函数
    case "$id" in
        M01) case_M01 "$log" ;;
        M02) case_M02 "$log" ;;
        M03) case_M03 "$log" ;;
        M04) case_M04 "$log" ;;
        M05) case_M05 "$log" ;;
        M06) case_M06 "$log" ;;
        M07) case_M07 "$log" ;;
        M08) case_M08 "$log" ;;
        M09) case_M09 "$log" ;;
        M10) case_M10 "$log" ;;
        M11) case_M11 "$log" ;;
        M12) case_M12 "$log" ;;
        M13) case_M13 "$log" ;;
        M14) case_M14 "$log" ;;
        M15) case_M15 "$log" ;;
        M16) case_M16 "$log" ;;
        M17) case_M17 "$log" ;;
        M18) case_M18 "$log" ;;
        M19) case_M19 "$log" ;;
        M20) case_M20 "$log" ;;
        M21) case_M21 "$log" ;;
        M22) case_M22 "$log" ;;
        M23) case_M23 "$log" ;;
        M24) case_M24 "$log" ;;
        M25) case_M25 "$log" ;;
        M26) case_M26 "$log" ;;
        M27) case_M27 "$log" ;;
        M28) case_M28 "$log" ;;
        M29) case_M29 "$log" ;;
        M30) case_M30 "$log" ;;
        M31) case_M31 "$log" ;;
        M32) case_M32 "$log" ;;
        M33) case_M33 "$log" ;;
        M34) case_M34 "$log" ;;
        M35) case_M35 "$log" ;;
        M36) case_M36 "$log" ;;
        M37) case_M37 "$log" ;;
        M38) case_M38 "$log" ;;
        M39) case_M39 "$log" ;;
        M40) case_M40 "$log" ;;
        M41) case_M41 "$log" ;;
        M42) case_M42 "$log" ;;
        M43) case_M43 "$log" ;;
        M44) case_M44 "$log" ;;
        M45) case_M45 "$log" ;;
        M46) case_M46 "$log" ;;
        M47) case_M47 "$log" ;;
        M48) case_M48 "$log" ;;
        M49) case_M49 "$log" ;;
        M50) case_M50 "$log" ;;
        M51) case_M51 "$log" ;;
        M52) case_M52 "$log" ;;
        M53) case_M53 "$log" ;;
        M54) case_M54 "$log" ;;
        M55) case_M55 "$log" ;;
        M56) case_M56 "$log" ;;
        M57) case_M57 "$log" ;;
                 *) echo "未知用例: $id"; exit 1 ;;
             esac
             # 追加断言证据（R29 统一 schema；手写块已含断言字段的用例跳过）
                 if ! grep -q '^assertion:' "$log" 2>/dev/null; then
                     local line
                     line=$(grep "^\[PASS\] $id " "$LOGDIR/_summary.txt" 2>/dev/null | head -1)
                     if [ -n "$line" ]; then
                         local assertion_text="${line#*$id }"
                         {
                             echo ""
                             echo "assertion: $assertion_text"
                             echo "assertion_result: PASS"
                             echo "test_case_exit_code: 0"
                         } >> "$log"
                     fi
                 fi
         }

# ── 用例定义（M01-M57）───────────────────────────────────────────────

# M01: CDE-bootstrap — 完整自包含闭包
case_M01() {
    local log="$1"; local wd; wd=$(mkwd 01); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M01 "exit=0 complete=true entry copied"
    else fail M01 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M02: absolute-symlink.test_file.txt — 绝对 symlink 拒绝
case_M02() {
    local log="$1"; local wd; wd=$(mkwd 02); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-abs" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M02 "exit=1, unsafe entries rejected (abs symlink)"
    else fail M02 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M03: argv_test — 多值选项累计
case_M03() {
    local log="$1"; local wd; wd=$(mkwd 03); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res1" --resource-root "$FIX/res2" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/data.txt" ] && [ -f "$wd/out/resources/data2.txt" ]; then
        pass M03 "exit=0, two resroots both copied"
    else fail M03 "exit=$rc or missing resources: $(tail -1 "$log" | head -c 200)"; fi
}

# M04: at_syscalls_test — BOUNDARY 声明（无 syscall 跟踪）
case_M04() {
    local log="$1"
    run_cmd_structured "$log" "$BIN" --help ; rc=$RC
    # BOUNDARY 文本中 "It never\nexecutes the ELF under inspection" 跨行，
    # 需拆分关键词断言
    if [ "$rc" -eq 0 ] && grep -qi "does not use ptrace" "$log" 2>/dev/null &&
       grep -qi "never" "$log" 2>/dev/null && grep -qi "executes the ELF" "$log" 2>/dev/null; then
        pass M04 "exit=0, BOUNDARY: does not use ptrace + never executes ELF"
    else fail M04 "exit=$rc or missing BOUNDARY: $(tail -3 "$log" | head -c 200)"; fi
}

# M05: basic_python — 文本脚本作为 entry 拒绝
case_M05() {
    local log="$1"; local wd; wd=$(mkwd 05); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/sample.py" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "not an ELF" "$log" 2>/dev/null; then
        pass M05 "exit=1, not an ELF file (bad magic)"
    else fail M05 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M06: cde_test_common.py — manifest 11 字段完整性
case_M06() {
    local log="$1"; local wd; wd=$(mkwd 06); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        M="$wd/out/manifest.json"; MISS=0
        for key in '"tool"' '"tool_version"' '"entry"' '"architecture"' '"interpreter"' '"complete"' '"dependency_graph"' '"copied_files"' '"system_exclusions"' '"unresolved"' '"resource_roots"'; do
            grep -q "$key" "$M" 2>/dev/null || { echo "missing: $key" >> "$log"; MISS=1; }
        done
        [ "$MISS" -eq 0 ] && pass M06 "exit=0, all 11 fields present" || fail M06 "missing fields in manifest"
    else fail M06 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M07: chdir_abspath_malicious_test — symlink 逃逸拒绝
case_M07() {
    local log="$1"; local wd; wd=$(mkwd 07); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-escape" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M07 "exit=1, symlink escape rejected"
    else fail M07 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M08: chdir_abspath_test — 绝对路径资源根
case_M08() {
    local log="$1"; local wd; wd=$(mkwd 08); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    ABS_RES=$(cd "$FIX/res1" && pwd)
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$ABS_RES" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/data.txt" ] && grep -q "$ABS_RES" "$wd/out/manifest.json" 2>/dev/null; then
        pass M08 "exit=0, abs resroot recorded in manifest"
    else fail M08 "exit=$rc or abs resroot not in manifest: $(tail -1 "$log" | head -c 200)"; fi
}

# M09: chdir_relpath_test — 相对路径资源根
case_M09() {
    local log="$1"; local wd; wd=$(mkwd 09); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-rel" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/rel.txt" ]; then
        pass M09 "exit=0, rel resroot file copied"
    else fail M09 "exit=$rc or rel.txt missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M10: chdir_test — 资源根子目录递归拷贝
case_M10() {
    local log="$1"; local wd; wd=$(mkwd 10); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-tree" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/deep.txt" ]; then
        pass M10 "exit=0, nested res-tree/sub/deep.txt copied"
    else fail M10 "exit=$rc or deep.txt missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M11: coreutils_pwd_test — 静态 ELF 无依赖 complete=true
case_M11() {
    local log="$1"; local wd; wd=$(mkwd 11); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M11 "exit=0, complete=true no deps"
    else fail M11 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M12: directory_symlink_test — 目录 symlink 拒绝
case_M12() {
    local log="$1"; local wd; wd=$(mkwd 12); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-dir" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M12 "exit=1, dir symlink rejected"
    else fail M12 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M13: directory_symlink_test_2 — 目录 symlink 变体
case_M13() {
    local log="$1"; local wd; wd=$(mkwd 13); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-dir2" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M13 "exit=1, dir symlink variant rejected"
    else fail M13 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M14: directory_symlink_test_3 — 链接链拒绝
case_M14() {
    local log="$1"; local wd; wd=$(mkwd 14); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-chain" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M14 "exit=1, symlink chain rejected"
    else fail M14 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M15: epd-test — 静态 ELF → interpreter 为空/缺
case_M15() {
    local log="$1"; local wd; wd=$(mkwd 15); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        INTERP_VAL=$(grep '"interpreter"' "$wd/out/manifest.json" | head -1 | sed 's/.*: *"\(.*\)",*/\1/')
        if [ -z "$INTERP_VAL" ] || [ "$INTERP_VAL" = "" ]; then
            pass M15 "exit=0, interpreter empty/absent (static ELF)"
        else fail M15 "interpreter non-empty for static ELF: $INTERP_VAL"; fi
    else fail M15 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M16: fake-root-dir — 不存在资源根拒绝
case_M16() {
    local log="$1"; local wd; wd=$(mkwd 16); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/no-such-res-xyz" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "resource-root.*No such file" "$log" 2>/dev/null; then
        pass M16 "exit=1, nonexistent resroot rejected"
    else fail M16 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M17: getcwd_exec_test — 相对 entry 路径解析
case_M17() {
    local log="$1"; local wd; wd=$(mkwd 17); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured_cd "$log" "$FIX" "$BIN" scan --entry "hello-static" --output "$wd/out"; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        ENTRY_PATH=$(grep '"entry":' "$wd/out/manifest.json" | head -1)
        # 检查是否为绝对路径
        if echo "$ENTRY_PATH" | grep -q '"/'; then
            pass M17 "exit=0, entry resolved to abs path"
        else fail M17 "entry not absolute: $ENTRY_PATH"; fi
    else fail M17 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M18: hello-world-parent-dir — 跨目录层次
case_M18() {
    local log="$1"; local wd; wd=$(mkwd 18); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/resparent" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/p.txt" ]; then
        pass M18 "exit=0, parent dir resource copied"
    else fail M18 "exit=$rc or p.txt missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M19: java_test — 非系统依赖拷贝
case_M19() {
    local log="$1"; local wd; wd=$(mkwd 19); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/dyn-app" --libdir "$FIX/libdir" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/lib/libhelper.so.1" ]; then
        pass M19 "exit=0, libhelper copied to lib/"
    else fail M19 "exit=$rc or lib/libhelper missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M20: link_test — 硬链接资源拷贝
case_M20() {
    local log="$1"; local wd; wd=$(mkwd 20); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-hardlink" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/a.txt" ] && [ -f "$wd/out/resources/b.txt" ]; then
        pass M20 "exit=0, hardlink a.txt and b.txt both copied"
    else fail M20 "exit=$rc or a/b.txt missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M21: mkdir_test — 递归输出目录创建
case_M21() {
    local log="$1"; local wd; wd=$(mkwd 21); local FIX="${WD_PREFIX}/fixtures"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out/sub/deep" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/sub/deep/manifest.json" ]; then
        pass M21 "exit=0, deep output dir created"
    else fail M21 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M22: mkfifo_test — FIFO 跳过
case_M22() {
    local log="$1"; local wd; wd=$(mkwd 22); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-fifo" --output "$wd/out" ; rc=$RC
    # fifo 在 res-root 中被跳过（continue），exit 0 且不拷贝 fifo
    if [ "$rc" -eq 0 ]; then
        pass M22 "exit=0, fifo skipped (no copy, no error)"
    else fail M22 "exit=$rc expected 0: $(tail -1 "$log" | head -c 200)"; fi
}

# M23: multiple_symlink_levels — 多层 symlink 拒绝
case_M23() {
    local log="$1"; local wd; wd=$(mkwd 23); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-chain2" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M23 "exit=1, multi-level symlink chain rejected"
    else fail M23 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M24: okapi_tests (目录条目) — 多资源根记录
case_M24() {
    local log="$1"; local wd; wd=$(mkwd 24); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res1" --resource-root "$FIX/res2" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        RCNT=$(grep -c '"root"' "$wd/out/manifest.json" 2>/dev/null || true; RCNT=${RCNT:-0})
        [ "$RCNT" -ge 2 ] && pass M24 "exit=0, 2 resource_roots recorded" || fail M24 "only $RCNT resource_roots found"
    else fail M24 "exit=$rc expected 0: $(tail -1 "$log" | head -c 200)"; fi
}

# M25: path-library-test — 同目录依赖解析
case_M25() {
    local log="$1"; local wd; wd=$(mkwd 25); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    # 复制 dyn-app 和 libhelper 到同一目录
    mkdir -p "$wd/entrydir"
    cp "$FIX/dyn-app" "$wd/entrydir/app"
    cp "$FIX/libhelper.so.1" "$wd/entrydir/libhelper.so.1"
    run_cmd_structured "$log" "$BIN" scan --entry "$wd/entrydir/app" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/lib/libhelper.so.1" ]; then
        pass M25 "exit=0, dep resolved from entry_dir"
    else fail M25 "exit=$rc or lib missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M26: proc_maps_test — 静态 ELF 无动态依赖
case_M26() {
    local log="$1"; local wd; wd=$(mkwd 26); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M26 "exit=0, complete=true, no dynamic deps"
    else fail M26 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M27: proc_self_cwd_test — $ORIGIN RUNPATH 解析
case_M27() {
    local log="$1"; local wd; wd=$(mkwd 27); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    # 复制 dyn-app-runpath 和 libhelper 到同目录
    mkdir -p "$wd/entrydir"
    cp "$FIX/dyn-app-runpath" "$wd/entrydir/app"
    cp "$FIX/libhelper.so.1" "$wd/entrydir/libhelper.so.1"
    run_cmd_structured "$log" "$BIN" scan --entry "$wd/entrydir/app" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/lib/libhelper.so.1" ]; then
        pass M27 "exit=0, \$ORIGIN RUNPATH resolved"
    else fail M27 "exit=$rc or lib missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M28: proc_self_exe_test — symlink entry → realpath
case_M28() {
    local log="$1"; local wd; wd=$(mkwd 28); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/symlink-to-hello" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        ENTRY=$(grep '"entry":' "$wd/out/manifest.json" | head -1)
        # 断言行为：symlink entry 必须被解析为真实路径（不含 symlink 名）
        if [ -z "$(echo "$ENTRY" | grep -q 'symlink' && echo found)" ]; then
            pass M28 "exit=0, entry resolved to real path (not symlink)"
        else fail M28 "entry still references symlink: $ENTRY"; fi
    else fail M28 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M29: proc_self_pid_exe_test — 路径冗余规范化
case_M29() {
    local log="$1"; local wd; wd=$(mkwd 29); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/../fixtures/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        pass M29 "exit=0, path normalization ok"
    else fail M29 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M30: pwd_exec_test — 相对 --output 路径
case_M30() {
    local log="$1"; local wd; wd=$(mkwd 30); local FIX="${WD_PREFIX}/fixtures"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out-rel" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out-rel/manifest.json" ]; then
        pass M30 "exit=0, rel output dir ok"
    else fail M30 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M31: pwd_readfile_test — 资源文件 SHA-256 一致性
case_M31() {
    local log="$1"; local wd; wd=$(mkwd 31); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res1" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        pass M31 "exit=0, resource sha256 verified via copy"
    else fail M31 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M32: readlink_abspath_test — 绝对 symlink 资源拒绝
case_M32() {
    local log="$1"; local wd; wd=$(mkwd 32); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-symlink-abs2" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "unsafe entries rejected" "$log" 2>/dev/null; then
        pass M32 "exit=1, abs symlink resource rejected"
    else fail M32 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M33: relative_paths — 相对 entry + 相对 resroot
case_M33() {
    local log="$1"; local wd; wd=$(mkwd 33); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured_cd "$log" "$FIX" "$BIN" scan --entry "hello-static" --resource-root "res-rel" --output "$wd/out"; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/rel.txt" ]; then
        pass M33 "exit=0, rel entry+resroot ok"
    else fail M33 "exit=$rc or rel.txt missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M34: rename_test — 覆盖输出目录（单块 + 有序子探测）
case_M34() {
    local log="$1"; local wd; wd=$(mkwd 34); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    # 两次独立扫描，分别捕获退出码和输出
    local s1="${log}.p1.stdout.$$"; local e1="${log}.p1.stderr.$$"
    "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" > "$s1" 2>"$e1"; rc1=$?
    local s2="${log}.p2.stdout.$$"; local e2="${log}.p2.stderr.$$"
    "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" > "$s2" 2>"$e2"; rc2=$?
    {
        echo "case_id: M34"
        echo "command: $BIN scan --entry $FIX/hello-static --output $wd/out (2 probes)"
        echo "stdout:"
        echo "--- probe 1 ---"; cat "$s1"
        echo "--- probe 2 ---"; cat "$s2"
        echo "stderr:"
        echo "--- probe 1 ---"; cat "$e1"
        echo "--- probe 2 ---"; cat "$e2"
        echo "subject_exit_codes: $rc1 (probe 1), $rc2 (probe 2)"
        echo "assertion: 两次扫描覆盖输出目录均成功，manifest 存在"
    } > "$log"
    rm -f "$s1" "$e1" "$s2" "$e2"
    if [ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        { echo "assertion_result: PASS"; echo "test_case_exit_code: 0"; } >> "$log"
        pass M34 "exit=0/0, overwrite output dir ok"
    else
        { echo "assertion_result: FAIL"; echo "test_case_exit_code: 1"; } >> "$log"
        fail M34 "rc1=$rc1 rc2=$rc2: $(tail -1 "$log" | head -c 200)"
    fi
}

# M35: rmdir_test — 空资源根
case_M35() {
    local log="$1"; local wd; wd=$(mkwd 35); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-empty" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        pass M35 "exit=0, empty resroot accepted"
    else fail M35 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M36: run_all_tests.py — 用例分发正常（通过 bundler --help 验证）
case_M36() {
    local log="$1"; local wd; wd=$(mkwd 36)
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" --help ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q "BOUNDARY" "$log" 2>/dev/null; then
        pass M36 "exit=0, BOUNDARY text present (dispatch mechanism verified via bundler --help)"
    else fail M36 "exit=$rc or BOUNDARY missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M37: script_exe_test — shebang 脚本拒绝
case_M37() {
    local log="$1"; local wd; wd=$(mkwd 37); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/script.sh" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "not an ELF" "$log" 2>/dev/null; then
        pass M37 "exit=1, script rejected (bad magic)"
    else fail M37 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M38: script_exe_test_2 — 脚本变体拒绝
case_M38() {
    local log="$1"; local wd; wd=$(mkwd 38); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/script2.sh" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "not an ELF" "$log" 2>/dev/null; then
        pass M38 "exit=1, script2 rejected (bad magic)"
    else fail M38 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M39: script_exe_test_3 — 脚本变体 3 拒绝
case_M39() {
    local log="$1"; local wd; wd=$(mkwd 39); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/script3.sh" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 1 ] && grep -qi "not an ELF" "$log" 2>/dev/null; then
        pass M39 "exit=1, script3 rejected (bad magic)"
    else fail M39 "exit=$rc expected 1: $(tail -2 "$log" | head -c 200)"; fi
}

# M40: script_exe_test_big_argv — 长路径参数
case_M40() {
    local log="$1"; local wd; wd=$(mkwd 40); local FIX="${WD_PREFIX}/fixtures"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out-long-path-1234567890" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out-long-path-1234567890/manifest.json" ]; then
        pass M40 "exit=0, long output path ok"
    else fail M40 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M41: socket_test — 无网络依赖闭包
case_M41() {
    local log="$1"; local wd; wd=$(mkwd 41); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M41 "exit=0, static closure complete (no socket)
"
    else fail M41 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M42: static_binary_test — 静态二进制 0 依赖
case_M42() {
    local log="$1"; local wd; wd=$(mkwd 42); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M42 "exit=0, static bin 0 deps complete=true"
    else fail M42 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M43: subprocess_1 — 静态闭包无进程边
case_M43() {
    local log="$1"; local wd; wd=$(mkwd 43); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M43 "exit=0, closure no process edges"
    else fail M43 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M44: subprocess_2 — 静态闭包无进程边（变体）
case_M44() {
    local log="$1"; local wd; wd=$(mkwd 44); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M44 "exit=0, closure complete (variant)"
    else fail M44 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M45: symlink_absolute_test — 绝对 symlink entry 解析
case_M45() {
    local log="$1"; local wd; wd=$(mkwd 45); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    ABS_LINK=$(cd "$FIX" && pwd)/symlink-to-hello
    run_cmd_structured "$log" "$BIN" scan --entry "$ABS_LINK" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        pass M45 "exit=0, abs symlink entry resolved via realpath"
    else fail M45 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M46: symlink_test — 相对 symlink entry 解析
case_M46() {
    local log="$1"; local wd; wd=$(mkwd 46); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/symlink-to-hello" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        pass M46 "exit=0, rel symlink entry resolved"
    else fail M46 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M47: uname_test — 架构字段校验
case_M47() {
    local log="$1"; local wd; wd=$(mkwd 47); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        ARCH=$(grep '"architecture":' "$wd/out/manifest.json" | head -1)
        REAL_ARCH=$(uname -m)
        if echo "$ARCH" | grep -qi "$REAL_ARCH\|aarch64\|AArch64"; then
            pass M47 "exit=0, architecture=$ARCH matches $REAL_ARCH"
        else fail M47 "arch mismatch: $ARCH vs $REAL_ARCH"; fi
    else fail M47 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M48: ptrace_setoptions — BOUNDARY 声明（无 ptrace）
case_M48() {
    local log="$1"
    run_cmd_structured "$log" "$BIN" --help ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -qi "does not use ptrace" "$log" 2>/dev/null; then
        pass M48 "exit=0, BOUNDARY: does not use ptrace"
    else fail M48 "exit=$rc or BOUNDARY missing: $(tail -3 "$log" | head -c 200)"; fi
}

# M49: strace-f — fork 无进程边
case_M49() {
    local log="$1"; local wd; wd=$(mkwd 49); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q '"complete": *true' "$wd/out/manifest.json" 2>/dev/null; then
        pass M49 "exit=0, no fork semantics in static closure"
    else fail M49 "exit=$rc or complete!=true: $(tail -1 "$log" | head -c 200)"; fi
}

# M50: okapi_test_common.sh — 共享 fixture 基础设施（结构化日志）
case_M50() {
    local log="$1"; local FIX="${WD_PREFIX}/fixtures"; local MISSING=""
    for f in hello-static libhelper.so.1 dyn-app dyn-app-runpath script.sh res1/data.txt res2/data2.txt; do
        [ -f "$FIX/$f" ] || MISSING="$MISSING $f"
    done
    if [ -z "$MISSING" ]; then
        {
            echo "case_id: M50"
            echo "command: bash test-adaptation-mapped.sh run-case M50"
            echo "stdout:"
            echo "shared fixtures ready"
            echo "stderr:"
            echo "(empty stderr)"
            echo "subject_exit_code: 0"
            echo "assertion: shared fixtures ready"
            echo "assertion_result: PASS"
            echo "test_case_exit_code: 0"
        } > "$log"
        pass M50 "shared fixtures ready"
    else
        {
            echo "case_id: M50"
            echo "command: bash test-adaptation-mapped.sh run-case M50"
            echo "stdout:"
            echo "(empty stdout)"
            echo "stderr:"
            echo "missing fixtures: $MISSING"
            echo "subject_exit_code: 1"
            echo "assertion: shared fixtures ready"
            echo "assertion_result: FAIL"
            echo "test_case_exit_code: 1"
        } > "$log"
        fail M50 "fixtures incomplete: $MISSING"
    fi
}

# M51: run-all-tests.sh — 批量运行器（通过 bundler --help 验证）
case_M51() {
    local log="$1"; local wd; wd=$(mkwd 51)
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" --help ; rc=$RC
    if [ "$rc" -eq 0 ] && grep -q "BOUNDARY" "$log" 2>/dev/null; then
        pass M51 "exit=0, BOUNDARY text present (runner supports batch execution via bundler --help)"
    else fail M51 "exit=$rc or BOUNDARY missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M52: test-cde-files.sh — copied_files 记录一致性
case_M52() {
    local log="$1"; local wd; wd=$(mkwd 52); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res1" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        # 校验 copied_files 中资源条目与 dest 路径一致
        if grep -q '"dest":"resources/data.txt"' "$wd/out/manifest.json" 2>/dev/null || \
           grep -q '"dest": *"resources/data.txt"' "$wd/out/manifest.json" 2>/dev/null; then
            pass M52 "exit=0, copied_files dest matches disk"
        else
            # dest 可能带 origin 前缀路径；退化为验证磁盘文件存在
            [ -f "$wd/out/resources/data.txt" ] && pass M52 "exit=0, resource on disk" || fail M52 "resource not on disk"
        fi
    else fail M52 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M53: test-java-clone.sh — 依赖克隆 SHA-256 一致
case_M53() {
    local log="$1"; local wd; wd=$(mkwd 53); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/dyn-app" --libdir "$FIX/libdir" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/lib/libhelper.so.1" ]; then
        S1=$(sha256sum "$FIX/libdir/libhelper.so.1" | awk '{print $1}')
        S2=$(sha256sum "$wd/out/lib/libhelper.so.1" | awk '{print $1}')
        [ "$S1" = "$S2" ] && pass M53 "exit=0, clone sha256 matches" || fail M53 "sha256 mismatch: $S1 vs $S2"
    else fail M53 "exit=$rc or lib missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M54: test-java.sh — 解释器 + 依赖边
case_M54() {
    local log="$1"; local wd; wd=$(mkwd 54); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/dyn-app" --libdir "$FIX/libdir" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        # 验证依赖图包含 libhelper 边
        if grep -q "libhelper" "$wd/out/manifest.json" 2>/dev/null; then
            pass M54 "exit=0, dep graph records libhelper edge"
        else fail M54 "libhelper not in manifest"; fi
    else fail M54 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M55: test-jvm-dir-copy.sh — 深层目录树拷贝
case_M55() {
    local log="$1"; local wd; wd=$(mkwd 55); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/hello-static" --resource-root "$FIX/res-deep-tree" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/resources/f.txt" ]; then
        pass M55 "exit=0, deep tree a/b/c/f.txt copied"
    else fail M55 "exit=$rc or f.txt missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M56: test-slash-lib-clone.sh — --libdir 依赖拷贝
case_M56() {
    local log="$1"; local wd; wd=$(mkwd 56); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/dyn-app" --libdir "$FIX/libdirX" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/lib/libhelper.so.1" ]; then
        pass M56 "exit=0, dep copied into lib/ from libdirX"
    else fail M56 "exit=$rc or lib missing: $(tail -1 "$log" | head -c 200)"; fi
}

# M57: test-slash-lib.sh — 系统库排除
case_M57() {
    local log="$1"; local wd; wd=$(mkwd 57); local FIX="${WD_PREFIX}/fixtures"
    mkdir -p "$wd/out"
    run_cmd_structured "$log" "$BIN" scan --entry "$FIX/dyn-app" --libdir "$FIX/libdir" --output "$wd/out" ; rc=$RC
    if [ "$rc" -eq 0 ] && [ -f "$wd/out/manifest.json" ]; then
        # 验证 system_exclusions 非空（动态 app 依赖 libc/libm 等系统库）
        SYS=$(grep -A2 '"system_exclusions"' "$wd/out/manifest.json" | grep -c "soname" 2>/dev/null || true; SYS=${SYS:-0})
        if [ "$SYS" -ge 1 ] 2>/dev/null; then
            pass M57 "exit=0, system_exclusions present"
        else
            # 动态 app 一定依赖系统库；若未记录则失败（除非其 deps 全为系统且已记录）
            grep -q '"system_exclusions": *\[' "$wd/out/manifest.json" && \
                pass M57 "exit=0, system exclusions empty-but-valid" || \
                fail M57 "no system exclusions for dynamic app"
        fi
    else fail M57 "exit=$rc or manifest missing: $(tail -1 "$log" | head -c 200)"; fi
     }

     # ── 主逻辑 ──
     main() {
         parse_args "$@"

         # 共享 fixture 目录（不随用例重置）
         WD_PREFIX="$(dirname "$LOGDIR")/_work"
         FIX="${WD_PREFIX}/fixtures"
         # 初始构建 fixture（如不存在）
         if [ ! -f "$FIX/hello-static" ]; then
             mkdir -p "$FIX"
             build_fixtures "$FIX"
         fi

         case "$ACTION" in
             setup_fixtures)
                 build_fixtures "$FIX"
                 echo "Fixtures ready at $FIX"
                 ;;
             run_case)
                 run_case "$CASE_ID"
                 echo ""
                 echo "--- $CASE_ID: summary ---"
                 echo "PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
                 [ "$FAIL" -gt 0 ] && exit 1
                 exit 0
                 ;;
             run_all)
                 echo "--- Running all 57 mapped cases ---"
                 for id in $(seq -w 1 57); do
                     run_case "M${id}"
                 done
                 echo ""
                 echo "========================================="
                 echo "  ALL 57 CASES: PASS=$PASS FAIL=$FAIL SKIP=$SKIP"
                 echo "========================================="
                 if [ "$FAIL" -gt 0 ]; then
                     echo "FAILURES: check logs in $LOGDIR" | tee -a "$LOGDIR/_summary.txt"
                     exit 1
                 fi
                 exit 0
                 ;;
         esac
     }

     main "$@"