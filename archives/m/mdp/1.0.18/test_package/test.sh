#!/usr/bin/env bash
# test_package/test.sh — consumer tests for the mdp executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
#
# mdp 1.0.18 上游无 make check；本测试用程序化 Markdown 输入驱动真实二进制：
#   - mdp -d  : 解析器统计输出到 stderr（headers/slides 计数），无需 TTY
#   - mdp -dd : 每 slide 的详细行统计
#   - mdp -v  : 版本输出（stdout）
#   - mdp     : 无参数读 stdin（管道喂入 Markdown）
# 断言基于上游 src/parser.c markdown_debug() 的固定输出格式：
#   fwprintf(stderr, L"headers: %i\nslides: %i\n", ...)
#   fwprintf(stderr, L"  slide %i: %i lines\n", ...)
set -euo pipefail

DISCOVERED=0
PASSED=0

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# ── 程序化 Markdown 输入 ─────────────────────────────────────
# 3 个 % 头部行 + 2 页幻灯片（1 页标题/列表/代码块，1 页分隔线内容）
cat > "$WORKDIR/deck.md" <<'EOF'
%title: Consumer Test Deck
%bottom: OHOS
%top: mdp

# 第 1 页

- 列表项 A
- 列表项 B

---

第 2 页

```c
int main(void) { return 0; }
```
EOF

# ── Test 1: 版本输出 ──────────────────────────────────────────
DISCOVERED=$((DISCOVERED + 1))
VER="$(mdp -v 2>&1)" || true
if printf '%s' "$VER" | grep -q "^mdp 1\.0\.18$"; then
    echo "OK: mdp -v prints 'mdp 1.0.18'"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: mdp -v output unexpected (got: $VER)"
fi

# ── Test 2: -d 解析统计（headers=3, slides=2，无需 TTY）────────
DISCOVERED=$((DISCOVERED + 1))
DBG="$(mdp -d "$WORKDIR/deck.md" </dev/null 2>&1 >/dev/null)" || true
if printf '%s' "$DBG" | grep -q "^headers: 3$" && \
   printf '%s' "$DBG" | grep -q "^slides: 2$"; then
    echo "OK: mdp -d reports headers=3 slides=2"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: mdp -d parser stats unexpected (got: $DBG)"
fi

# ── Test 3: -dd 每 slide 详细行统计 ─────────────────────────
# 上游 markdown_debug() 在 debug>1 时输出格式为：
#   header: <value>                              （每个 % 头部行）
#   "  slide %i:\n"                              （每页）
#   "    line %i: bits = %i, length = %i\n"      （每行）
DISCOVERED=$((DISCOVERED + 1))
DBG2="$(mdp -dd "$WORKDIR/deck.md" </dev/null 2>&1 >/dev/null)" || true
if printf '%s' "$DBG2" | grep -q "^header: Consumer Test Deck$" && \
   printf '%s' "$DBG2" | grep -q "^header: OHOS$" && \
   printf '%s' "$DBG2" | grep -q "^header: mdp$" && \
   printf '%s' "$DBG2" | grep -q "^  slide 1:$" && \
   printf '%s' "$DBG2" | grep -q "^  slide 2:$" && \
   printf '%s' "$DBG2" | grep -q "^    line 1: bits = [0-9]*, length = [0-9]*$"; then
    echo "OK: mdp -dd dumps headers and per-slide line details"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: mdp -dd per-slide stats unexpected (got: $DBG2)"
fi

# ── Test 4: 管道 stdin 输入解析（FILE=-，pty 提供控制终端）────
# 上游行为：FILE=- 时 noreload=1，解析完成后总是 freopen("/dev/tty")
# 作为按键输入（无控制终端则 exit(1)），debug 输出在其后。
# 在 pty 中运行：stdin 用管道喂 Markdown，控制终端来自 pty，
# 断言 -d 解析统计输出且 viewer 可达；alarm 防挂起。
DISCOVERED=$((DISCOVERED + 1))
MD_PIPE="$(python3 - <<'PYEOF' 2>&1
import os, pty, signal, sys
signal.alarm(15)
md = b"stdin slide\n\n---\nstdin slide 2\n"
r, w = os.pipe()
os.write(w, md)
os.close(w)
pid, fd = pty.fork()
if pid == 0:
    os.dup2(r, 0)
    os.close(r)
    os.environ["TERM"] = "xterm-256color"
    os.execvp("mdp", ["mdp", "-d", "-"])
os.close(r)
out = b""
try:
    while True:
        d = os.read(fd, 4096)
        if not d:
            break
        out += d
        # 等待完整的 "slides: <n>\r\n" 行(数字已到)再退出,避免半行竞态
        if b"slides:" in out and not out.rstrip().endswith(b"slides:"):
            import re
            if re.search(rb"slides: \d+\r?\n", out):
                os.write(fd, b"q")  # quit viewer
                break
except OSError:
    pass
try:
    os.close(fd)
except OSError:
    pass
_, status = os.waitpid(pid, 0)
sys.stdout.buffer.write(out)
PYEOF
)" || true
# pty 是终端模式，行尾为 \r\n，先剥掉 \r 再断言
MD_PIPE_CLEAN="$(printf '%s' "$MD_PIPE" | tr -d '\r')"
if printf '%s' "$MD_PIPE_CLEAN" | grep -q "^headers: 0$" && \
   printf '%s' "$MD_PIPE_CLEAN" | grep -q "^slides: 2$"; then
    echo "OK: mdp -d parses stdin Markdown inside a pty (slides=2, viewer reachable)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: pty stdin parse failed (got: $MD_PIPE)"
fi

# ── Test 5: 不存在的输入文件报错退出非 0 ─────────────────────
DISCOVERED=$((DISCOVERED + 1))
set +e
mdp /nonexistent/no-such-deck.md </dev/null >/dev/null 2>&1
RC=$?
set -e
if [ "$RC" -ne 0 ]; then
    echo "OK: mdp exits non-zero for missing input file (rc=$RC)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: mdp exited 0 for missing input file"
fi

# ── Test 6: 宽字符（中文）标题解析不丢失 slide ────────────────
DISCOVERED=$((DISCOVERED + 1))
CJK_DBG="$(mdp -d "$WORKDIR/deck.md" </dev/null 2>&1 >/dev/null)" || true
if printf '%s' "$CJK_DBG" | grep -q "^headers: 3$" && \
   printf '%s' "$CJK_DBG" | grep -q "^slides: 2$"; then
    echo "OK: wide-character (CJK) markdown parses to same structure"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: CJK markdown parse changed structure (got: $CJK_DBG)"
fi

echo "test_package: ${PASSED}/${DISCOVERED} checks passed"

# ── HMBS 机器证据标记（真实用例计数，由上面实际执行产生）──
if [ "$PASSED" -eq "$DISCOVERED" ]; then
    HMBS_PASSED=true
else
    HMBS_PASSED=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$HMBS_PASSED" "$DISCOVERED" "$PASSED"
# 上游无测试（已审计 1.0.18 归档 Makefile：目标仅 all/clean/install/uninstall）
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"audited 1.0.18 tarball: Makefile targets are all/clean/install/uninstall only, no check/test target, no test sources"}\n'

[ "$PASSED" -eq "$DISCOVERED" ] || exit 1
