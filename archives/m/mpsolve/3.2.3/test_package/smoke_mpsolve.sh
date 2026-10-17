#!/bin/sh
# mpsolve 3.2.3 consumer test (R34: runs the packaged binary, asserts behavior).
#
# 上游 `make check` 的 16 个 check(3) 程序全部 link ${top_builddir}/src/libmps/
# libmpsprivate.la, 只覆盖 libmps 的 C API, **从不执行安装树里的 bin/mpsolve**。
# 本脚本补的正是这一层: 安装出来的 CLI 在"无 tty / 无 DISPLAY / 不可写临时目录"
# 的退化环境下能否照常给出正确结果 —— 这正是 OHOS(HMFS /tmp 只读、无桌面栈)的
# 运行约束。
#
# 10 条断言, 三组:
#   A 版本握手 + 批处理基本路径 (4)
#   B 输出格式旋钮真的生效, 且默认值不撒谎 (3, 含一条反向验证)
#   C 退化环境 (无 tty / 无 DISPLAY / HOME 未设 / TEMP/TMPDIR 不可写) (3)
#
# 只用 POSIX sh 内建 + grep (3.2.1 同款); 不假设 tr/strings/awk 存在。
BIN="$1"
fail() { echo "smoke_mpsolve: FAIL - $*" >&2; exit 1; }

TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/poly.txt" <<'EOF'
! x^2 - 2
Degree=2;
Monomial;
Real;
Integer;
-2
0
1
EOF

# ---------- A: 版本握手 + 批处理基本路径 ----------
# mpsolve 没有 --version(该入参落进 usage 分支); 版本握手是 -v, 恰好一行。
V=$("$BIN" -v 2>"$TMP/err.txt"); rc=$?
[ $rc -eq 0 ] || fail "-v exited $rc: $(head -3 "$TMP/err.txt")"
[ "$V" = "MPSolve 3.2.3" ] || fail "-v printed '$V', expected 'MPSolve 3.2.3'"          # A1

"$BIN" "$TMP/poly.txt" > "$TMP/out.txt" 2>"$TMP/err.txt"; rc=$?
[ $rc -eq 0 ] || fail "default run exited $rc: $(head -5 "$TMP/err.txt")"                # A2
# MPSolve prints roots in scientific notation, e.g. "(-0.14142135623731e1, 0.e-19)"
grep -qE '\(0\.1414213[0-9]*e1' "$TMP/out.txt" || {                                    # A3
    echo "positive root sqrt(2) not found" >&2; head -10 "$TMP/out.txt" >&2; exit 1; }
grep -qE '\(-0\.1414213[0-9]*e1' "$TMP/out.txt" || {                                    # A4
    echo "negative root -sqrt(2) not found" >&2; head -10 "$TMP/out.txt" >&2; exit 1; }

# ---------- B: 输出格式旋钮 ----------
# 默认(compact)格式只打印 14 位有效数字、且不带 Status 行; -O f(full) 才把内部
# 表示整段倒出来(21 位有效数字 + 每根一行 Status)。先做反向验证, 证明默认值确实
# 不是 full —— 否则 B2/B3 可能是永远为真的断言。
grep -qE '\(0\.1414213562373095' "$TMP/out.txt" && \
    fail "default output already carries >=16 digits; -O f assertion would be vacuous"
grep -q 'Status:' "$TMP/out.txt" && \
    fail "default output already carries Status:, -O f assertion would be vacuous"      # B1

"$BIN" -O f "$TMP/poly.txt" > "$TMP/full.txt" 2>"$TMP/err.txt"; rc=$?
[ $rc -eq 0 ] || fail "-O f exited $rc: $(head -5 "$TMP/err.txt")"
grep -qE '\(0\.1414213562373095' "$TMP/full.txt" || {                                   # B2
    echo "-O f did not raise printed precision to >=16 digits" >&2
    head -10 "$TMP/full.txt" >&2; exit 1; }
grep -q 'Status:' "$TMP/full.txt" || {                                                  # B3
    echo "-O f did not emit the full-format Status line" >&2
    head -10 "$TMP/full.txt" >&2; exit 1; }

# ---------- C: 退化环境 (鸿蒙特有) ----------
# 无 tty(stdin/stdout 都是管道) + 无 DISPLAY + HOME 未设 + TEMP/TMPDIR 指向一个
# 不存在的目录(HMFS /tmp 只读的等价约束): CLI 必须静默退化, 仍以 0 退出并给出
# 两个正确根。环境改动用 subshell + unset + 行内赋值, 全部是 sh 内建。
(
    unset DISPLAY HOME
    TMPDIR="$TMP/no-such-tmpdir" TEMP="$TMP/no-such-tmpdir" \
        "$BIN" "$TMP/poly.txt" < /dev/null > "$TMP/deg.txt" 2>"$TMP/err.txt"
)
rc=$?
[ $rc -eq 0 ] || fail "degraded-env run exited $rc: $(head -5 "$TMP/err.txt")"          # C1
grep -qE '\(0\.1414213[0-9]*e1' "$TMP/deg.txt" || {                                     # C2
    echo "degraded-env run lost the positive root" >&2
    head -10 "$TMP/deg.txt" >&2; exit 1; }
grep -qE '\(-0\.1414213[0-9]*e1' "$TMP/deg.txt" || {                                    # C3
    echo "degraded-env run lost the negative root" >&2
    head -10 "$TMP/deg.txt" >&2; exit 1; }

echo "mpsolve smoke ok: version handshake, +/-sqrt(2) batch solve, -O f format knob," \
     "degraded-env headless run (10 assertions)"
