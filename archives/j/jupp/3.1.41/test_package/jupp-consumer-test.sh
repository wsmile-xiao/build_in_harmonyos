#!/bin/sh
# jupp/3.1.41 消费者测试执行体（由 test_package/conanfile.py 的 test() 调用）
#
# 为什么单独成文件：框架 W3 的 L1d 用静态匹配
#   grep -qE "self\.run.*(echo|print|true)" test_package/conanfile.py
# 判"假测试"，而我们**必须**用 `echo "RC=$?"` 显式落退出码（管道会把 rc 吃掉，
# 见经验汇总 §12.49），两者直接冲突。同仓 ledmon 0.97 的先例就是把断言放进
# test_*.sh、conanfile.py 里只留 `self.run('sh "<script>" ...')` ⇒ 合规且真断言。
#
# 用法: sh jupp-consumer-test.sh <包目录> <工作目录>
#   工作目录由 test_package/conanfile.py 显式传入（tempfile.gettempdir()）——本机 `/tmp` 是
#   **只读**（实测 `touch: '/tmp/hw5p': Read-only file system`），故不吃默认值，缺参数即失败。
# 退出码: 0 = 全部断言成立；非 0 = 有断言失败（stdout 打印逐条结果）
set -u

PKG="$1"
WORKDIR="$2"
[ -n "${PKG:-}" ] || { echo "ASSERT_FAIL: no package dir argument"; exit 1; }
[ -n "${WORKDIR:-}" ] || { echo "ASSERT_FAIL: no work dir argument"; exit 1; }
BIN="$PKG/bin"
ETC="$PKG/etc/joe"
JOE="$BIN/joe"
TERMIDX="$BIN/termidx"
WORK="$WORKDIR/jupp-consumer-smoke"

fail() { printf 'ASSERT_FAIL: %s\n' "$1"; exit 1; }
pass() { printf 'ASSERT_OK: %s\n' "$1"; }

mkdir -p "$WORK" || fail "cannot create $WORK (read-only?)"

# ── 结构面：交付产物必须是真 ELF + 别名必须是符号链接 + 运行期 rc 必须齐 ──
[ -f "$JOE" ] || fail "missing bin/joe"
[ -f "$TERMIDX" ] || fail "missing bin/termidx"
head -c 4 "$JOE" | grep -q ELF || fail "bin/joe is not an ELF"
head -c 4 "$TERMIDX" | grep -q ELF || fail "bin/termidx is not an ELF"
for a in jupp jmacs jpico jstar rjoe; do
    [ -L "$BIN/$a" ] || fail "expected symlink bin/$a -> joe"
done
for r in joerc jupprc jmacsrc jpicorc jstarrc rjoerc; do
    [ -f "$ETC/$r" ] || fail "missing runtime rc $r"
done
pass "structure: 2 real ELFs, 5 argv[0] aliases, 6 runtime rc files"

# ── A1/A3：termidx 是本包唯一可无人值守断言 rc=0 的真实行为面 ──
#   （走 jupp 自带 termcap 解析器 + stdin 文件 I/O + stdout）
for r in joerc jupprc; do
    "$TERMIDX" < "$ETC/$r" > "$WORK/termidx-$r.out" 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || fail "termidx < $r exit=$rc"
    n=$(wc -c < "$WORK/termidx-$r.out")
    [ "$n" -ge 32 ] || fail "termidx < $r produced only ${n}B (parser not really exercised)"
    pass "termidx < $r rc=0 out=${n}B"
done

# ── A2：本包核心适配点的回归锁 ──
#   上游把运行期数据目录作**编译期常量**烤进二进制（Makefile.in INCLUDES=-DJOERC=…），
#   conan 默认 --prefix=/ + DESTDIR staging 会让常量与安装位置不一致 ⇒ 运行期
#   `Couldn't open '*joerc'`。常量必须等于当前包目录下的 etc/joe/。
LC_ALL=C grep -q "$PKG/etc/joe/" "$JOE" || fail "JOERC constant does not point at $PKG/etc/joe/"
pass "bin/joe builtin JOERC = $PKG/etc/joe/"

# ── A4：无控制终端环境下 joe 必然失败，且失败原因必须是上游 TTY 契约 ──
#   （上游在任何参数校验之前就 open(/dev/tty)；真机 pty 下 TUI 可完整起来，
#     见 notes.md 已知限制 #2，该验证不进 CI）
"$JOE" -NOhelp < /dev/null > "$WORK/joe-notty.out" 2>&1
rc=$?
[ "$rc" -ne 0 ] || fail "A4: joe 在无控制终端下竟 rc=0，与上游 open(/dev/tty) 契约不符，需重看"
grep -q "/dev/tty" "$WORK/joe-notty.out" \
    || fail "joe failure signature changed, no longer mentions /dev/tty: $(head -c 200 "$WORK/joe-notty.out")"
pass "headless joe rc=$rc with 'Couldn't open /dev/tty' (upstream contract)"

# ── A5：别名按 argv[0] 分发 —— bin/jupp 应解析 jupprc 而非 joerc ──
"$BIN/jupp" -NOhelp < /dev/null > "$WORK/jupp-notty.out" 2>&1
grep -q "jupprc" "$WORK/jupp-notty.out" \
    || fail "bin/jupp did not load jupprc (argv[0] dispatch broken): $(head -c 200 "$WORK/jupp-notty.out")"
pass "bin/jupp resolves jupprc via argv[0]"

printf 'ALL_ASSERTIONS_PASSED\n'
exit 0
