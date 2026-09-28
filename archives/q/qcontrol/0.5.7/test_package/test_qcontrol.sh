#!/usr/bin/env bash
# test_package/test_qcontrol.sh — qcontrol 0.5.7 消费者行为测试（HarmonyOS PC）
#
# 用法: test_qcontrol.sh <pkg>/bin/qcontrol <pkg>/share/qcontrol
# 由 test_package/conanfile.py 的 test() 在 conan create 的 test 阶段真实执行，
# 全部断言 fail closed：任何一次不符预期的退出码 / 缺输出 / 崩溃都直接判失败。
#
# 口径说明（rule4）：本包不做"只打印/只查文件"式测试。每条断言都以使用者身份
# 调用打包后的 qcontrol 二进制，由它自己的 argv 解析、内嵌 Lua 配置解释器和
# 命令派发逻辑产出结果，再对这些结果做字符串/退出码断言。
#
# 覆盖的上游能力面（都是 qcontrol.c 里真实存在的代码路径）：
#   1  -V / --version 打印上游 CPPFLAGS 注入的版本宏，rc=0
#   2  --direct --help 打印 usage
#   3  --direct 模式下 Lua 配置里 register("system-status") 真的把 C 模块
#      装进命令表（help 列表里出现命令名与其 shorthelp）
#   4  confdir() 用 glob 载入目录里的 *.conf（musl glob 行为）
#   5  CLI -> C 命令 -> 内嵌 Lua 函数 -> C 的 logprint -> stdout 的完整往返
#   6  命令参数个数校验（缺参数 -> 非零退出，不崩溃）
#   7  未知命令 -> 非零退出，不崩溃
#   8  配置文件语法错误 -> Lua 诊断里带上出错文件名，进程优雅退出
#   9  配置文件不存在 -> "cannot open" 诊断，进程优雅退出（上游设计如此）
#   10 默认 client 模式连硬编码 AF_UNIX 路径 /var/run/qcontrol.sock：
#      无守护进程时优雅报错并非零退出（平台能力面记录，见输出 [cap] 行）
set -uo pipefail

BIN="${1:-}"
SHARE="${2:-}"

fail() { echo "FAIL: $*" >&2; exit 1; }

[ -n "$BIN" ] || fail "usage: test_qcontrol.sh <pkg>/bin/qcontrol <pkg>/share/qcontrol>"
[ -x "$BIN" ] || fail "packaged binary not executable: $BIN"
BIN="$(cd "$(dirname "$BIN")" && pwd)/$(basename "$BIN")"

N=0
ok() { N=$((N + 1)); echo "OK: $*"; }

# 真实运行被测二进制：捕获 stdout+stderr 与退出码（非零退出不中止脚本）
OUT=""
RC=0
run_bin() {
  OUT="$(timeout 30 "$BIN" "$@" 2>&1)"
  RC=$?
}

# 崩溃守卫：超时 / 信号致死 / 崩溃标记一律判失败。
# 255 不是信号：main() 里 `return -1` 在 shell 层就是 255（128+127 的 127 号信号不存在），
# 它正是上游"命令失败"的返回码，所以单独放行并由各个断言自己核数值。
no_crash() {
  local label="$1"
  if [ "$RC" -eq 124 ]; then
    printf '%s\n' "$OUT" >&2
    fail "$label timed out after 30s (blocking on something unexpected)"
  fi
  if [ "$RC" -ge 128 ] && [ "$RC" -ne 255 ]; then
    printf '%s\n' "$OUT" >&2
    fail "$label died from a signal (rc=$RC)"
  fi
  if printf '%s' "$OUT" | grep -qE 'Segmentation fault|core dumped|Bus error|Aborted|Illegal instruction'; then
    printf '%s\n' "$OUT" >&2
    fail "$label printed a crash marker"
  fi
}

TMPD="$(mktemp -d "${TMPDIR:-$HOME/tmp}/qcontrol-test.XXXXXX")" \
  || fail "mktemp -d failed (TMPDIR=${TMPDIR:-unset})"
trap 'rm -rf "$TMPD"' EXIT HUP INT TERM
# 调用方（conan test()）的 cwd 可能已被重建，先把 cwd 钉在一个必然存在的目录，
# 免得 getcwd 噪声混进断言输出。
cd "$HOME" || fail "cd $HOME failed"

CONF="$TMPD/qcontrol.conf"
CONFDIR="$TMPD/conf.d"
BADCONF="$TMPD/syntax-error.conf"
MISSCONF="$TMPD/does-not-exist.conf"
mkdir -p "$CONFDIR" || fail "mkdir $CONFDIR failed"

# 主配置：注册 system-status 模块、递归载入 conf.d、并定义被 C 侧回调的 Lua 函数
cat > "$CONF" <<EOF
register("system-status")
confdir("$CONFDIR")
function system_status(msg)
  logprint("qcontrol-fixture: status=" .. msg)
end
EOF
cat > "$CONFDIR/dropin.conf" <<EOF
logprint("qcontrol-fixture: confdir-loaded")
EOF
printf 'function broken(\n' > "$BADCONF"

# ── 1  --version ──────────────────────────────────────────────────────────
run_bin --version
no_crash "qcontrol --version"
[ "$RC" -eq 0 ] || { printf '%s\n' "$OUT" >&2; fail "--version rc=$RC, expected 0"; }
[ "$OUT" = "qcontrol 0.5.7" ] \
  || { printf '%s\n' "$OUT" >&2; fail "--version printed [$OUT], expected exactly [qcontrol 0.5.7]"; }
ok "1 --version reports the upstream version macro, rc=0"

# ── 2  -V（短选项同义） ───────────────────────────────────────────────────
run_bin -V
no_crash "qcontrol -V"
[ "$RC" -eq 0 ] && [ "$OUT" = "qcontrol 0.5.7" ] \
  || { printf '%s\n' "$OUT" >&2; fail "-V rc=$RC out=[$OUT], expected rc=0 and [qcontrol 0.5.7]"; }
ok "2 -V short option agrees with --version"

# ── 3  --direct --help（带本包配置）：usage 文本 ──────────────────────────
run_bin --direct -c "$CONF" --help
no_crash "qcontrol --direct -c CONF --help"
[ "$RC" -eq 0 ] || { printf '%s\n' "$OUT" >&2; fail "--direct --help rc=$RC, expected 0"; }
printf '%s' "$OUT" | grep -qF 'Usage: qcontrol [OPTION...] [command] [args...]' \
  || { printf '%s\n' "$OUT" >&2; fail "usage string missing from --direct --help output"; }
ok "3 --direct --help prints the upstream usage block"

# ── 4  Lua 配置被内嵌解释器执行：confdir 的 glob 载入 ────────────────────
printf '%s' "$OUT" | grep -qF 'qcontrol-fixture: confdir-loaded' \
  || { printf '%s\n' "$OUT" >&2; fail "confdir() did not load $CONFDIR/*.conf via glob"; }
ok "4 confdir() glob-included a second config file through the Lua interpreter"

# ── 5  register() 把 C 模块装进命令表 ────────────────────────────────────
printf '%s' "$OUT" | grep -qF 'Available commands are:' \
  || { printf '%s\n' "$OUT" >&2; fail "command list header missing"; }
printf '%s' "$OUT" | grep -qF 'system-status' \
  || { printf '%s\n' "$OUT" >&2; fail "register(system-status) did not reach the command table"; }
printf '%s' "$OUT" | grep -qF 'Signal system status' \
  || { printf '%s\n' "$OUT" >&2; fail "shorthelp of the registered command missing"; }
ok "5 Lua register() populated the C command table (name + shorthelp listed)"

# ── 6  完整往返：argv -> C 命令 -> Lua 函数 -> logprint -> stdout ─────────
run_bin --direct -c "$CONF" system-status start
no_crash "qcontrol --direct system-status start"
[ "$RC" -eq 0 ] || { printf '%s\n' "$OUT" >&2; fail "system-status start rc=$RC, expected 0"; }
printf '%s' "$OUT" | grep -qF 'qcontrol-fixture: status=start' \
  || { printf '%s\n' "$OUT" >&2; fail "CLI->C->Lua->logprint round trip did not deliver argv: [$OUT]"; }
ok "6 argv reached the Lua handler and its logprint output came back"

# ── 7  参数个数校验（缺 mandatory argument） ─────────────────────────────
run_bin --direct -c "$CONF" system-status
no_crash "qcontrol --direct system-status (no argument)"
[ "$RC" -eq 255 ] || { printf '%s\n' "$OUT" >&2; fail "missing command argument: rc=$RC, expected 255 (main returns -1)"; }
ok "7 arity check rejects a command invoked without its argument (rc=255)"

# ── 8  未知命令 ──────────────────────────────────────────────────────────
run_bin --direct -c "$CONF" definitely-not-a-command
no_crash "qcontrol --direct unknown command"
[ "$RC" -eq 255 ] || { printf '%s\n' "$OUT" >&2; fail "unknown command: rc=$RC, expected 255"; }
ok "8 unknown command exits with upstream's failure code 255 without crashing"

# ── 9  配置文件语法错误：Lua 诊断带文件名，进程优雅退出 ──────────────────
run_bin --direct -c "$BADCONF"
no_crash "qcontrol --direct with a syntactically broken config"
printf '%s' "$OUT" | grep -qF 'syntax-error.conf' \
  || { printf '%s\n' "$OUT" >&2; fail "Lua syntax diagnostic does not name the broken config file"; }
[ "$RC" -eq 0 ] || { printf '%s\n' "$OUT" >&2; fail "broken config: rc=$RC, expected 0 (upstream treats a failed config load as non-fatal in --direct)"; }
ok "9 a broken config yields a Lua error naming the file, and --direct stays non-fatal (rc=0)"

# ── 10 配置文件不存在：上游把 "cannot open" 当诊断而非致命错误 ────────────
run_bin --direct -c "$MISSCONF"
no_crash "qcontrol --direct with a missing config"
printf '%s' "$OUT" | grep -qF 'cannot open' \
  || { printf '%s\n' "$OUT" >&2; fail "missing-config diagnostic 'cannot open' not found: [$OUT]"; }
[ "$RC" -eq 0 ] || { printf '%s\n' "$OUT" >&2; fail "missing config: rc=$RC, expected 0"; }
ok "10 missing config file reports the upstream 'cannot open' diagnostic (rc=0)"

# ── 11 默认 client 模式：硬编码 /var/run/qcontrol.sock 的能力面记录 ───────
run_bin -c "$CONF" system-status start
no_crash "qcontrol (client mode, no daemon)"
printf '%s' "$OUT" | grep -qE 'socket' \
  || { printf '%s\n' "$OUT" >&2; fail "client mode exited without any socket diagnostic (rc=$RC)"; }
echo "[cap] client mode rc=$RC diagnostic: $(printf '%s' "$OUT" | grep -E 'socket' | head -n1)"
[ "$RC" -eq 255 ] \
  || fail "client mode without a daemon: rc=$RC, expected 255 (socket error swallowed or a daemon is running)"
ok "11 client mode without a daemon fails gracefully on the socket path (rc=255)"

echo "BEHAVIORAL ASSERTIONS PASSED: $N/$N"
