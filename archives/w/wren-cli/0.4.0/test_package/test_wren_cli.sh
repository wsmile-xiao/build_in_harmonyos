#!/bin/sh
# Consumer test for wren-cli/0.4.0 — drives the *installed* wren_cli binary.
# POSIX sh only (device runs mksh, CI worker runs bash); every assertion is a
# real process invocation, so the suite fails hard when bin/ is missing.
set -u

EXE="${1:-}"
TOTAL=0
PASS=0
FAIL=0

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  printf '[PASS] %s\n' "$1"
}

bad() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  printf '[FAIL] %s\n' "$1"
}

# eq <name> <want> <got>
eq() {
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1: want [$2] got [$3]"; fi
}

# has <name> <needle> <haystack>
has() {
  case "$3" in
    *"$2"*) ok "$1" ;;
    *) bad "$1: [$2] absent from [$3]" ;;
  esac
}

# ne <name> <notwant> <got>
ne() {
  if [ "$2" != "$3" ]; then ok "$1"; else bad "$1: value must not be [$2]"; fi
}

if [ ! -x "$EXE" ]; then
  printf '[FAIL] wren_cli is installed and executable (got [%s])\n' "$EXE"
  printf 'TOTAL=1 PASS=0 FAIL=1\n'
  exit 1
fi
ok 'bin/wren_cli installed and executable'

# /tmp is read-only on HarmonyOS: keep scratch inside the (writable) work dir.
BASE=$PWD
WORK="$BASE/.wrencli-$$"
mkdir -p "$WORK" 2>/dev/null || WORK="$HOME/.wrencli-$$"
mkdir -p "$WORK" || { printf 'TOTAL=1 PASS=0 FAIL=1\n'; exit 1; }
cd "$WORK" || exit 1
PHYS=$(pwd -P 2>/dev/null || pwd)
cleanup() { cd "$BASE" 2>/dev/null || cd / ; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------- version/help
out=$("$EXE" --version 2>&1); rc=$?
eq '--version exits 0' '0' "$rc"
eq '--version reports upstream Wren version' 'wren 0.4.0' "$out"

out=$("$EXE" --help 2>&1); rc=$?
eq '--help exits 0' '0' "$rc"
has '--help prints usage line' 'Usage:' "$out"
has '--help lists --version' '--version' "$out"

# ------------------------------------------------------------------- language
cat > hello.wren <<'EOF'
System.print("hello")
EOF
out=$("$EXE" hello.wren 2>/dev/null); rc=$?
eq 'script run exits 0' '0' "$rc"
eq 'System.print reaches stdout' 'hello' "$out"

cat > interp.wren <<'EOF'
class Greeter {
  static greet(name) { "wren %(name)" }
}
System.print(Greeter.greet(6 * 7))
EOF
out=$("$EXE" interp.wren 2>/dev/null)
eq 'class + interpolation + arithmetic' 'wren 42' "$out"

cat > seq.wren <<'EOF'
var xs = [3, 1, 2]
System.print(xs.count)
System.print(xs[1])
EOF
out=$("$EXE" seq.wren 2>/dev/null)
eq 'list count and index' '3
1' "$out"

# Negative control: proves the harness compares real program output instead of
# echoing a fixed string (a broken "always hello" binary would still pass above).
cat > other.wren <<'EOF'
System.print("not_hello")
EOF
out=$("$EXE" other.wren 2>/dev/null)
ne 'negative control differs from hello' 'hello' "$out"
eq 'negative control reports its own value' 'not_hello' "$out"

# ------------------------------------------------------------------ error paths
cat > badsyntax.wren <<'EOF'
System.print("unterminated
EOF
out=$("$EXE" badsyntax.wren 2>/dev/null); rc=$?
err=$("$EXE" badsyntax.wren 2>&1 >/dev/null)
eq 'compile error exits EX_DATAERR (65)' '65' "$rc"
has 'compile error reported on stderr' 'Error' "$err"

cat > badruntime.wren <<'EOF'
import "io" for Directory
Directory.exists(123)
EOF
"$EXE" badruntime.wren >/dev/null 2>&1; rc=$?
err=$("$EXE" badruntime.wren 2>&1 >/dev/null)
eq 'runtime error exits EX_SOFTWARE (70)' '70' "$rc"
has 'runtime error message reaches stderr' 'Path must be a string.' "$err"

# ------------------------------------------------ libuv-backed modules on OHOS
cat > fileio.wren <<'EOF'
import "io" for File
File.create("note.tmp") {|file| file.writeBytes("stuff") }
System.print(File.size("note.tmp"))
System.print(File.read("note.tmp"))
File.delete("note.tmp")
System.print(File.exists("note.tmp"))
EOF
# 断言的是程序的 stdout，stderr 一律丢弃：stdout 在被管道捕获时是块缓冲的，
# 把 stderr 一起并进来时，未缓冲的 stderr 会抢先落进流里、把行号错位（上一轮就是这么红了一条）。
out=$("$EXE" fileio.wren 2>/dev/null); rc=$?
eq 'file roundtrip exits 0' '0' "$rc"
eq 'File.size after writeBytes' '5' "$(printf '%s' "$out" | sed -n '1p')"
eq 'File.read roundtrip' 'stuff' "$(printf '%s' "$out" | sed -n '2p')"
eq 'File.delete removes it' 'false' "$(printf '%s' "$out" | sed -n '3p')"

cat > dirio.wren <<'EOF'
import "io" for Directory, File
Directory.create("sub")
File.create("sub/only.txt") {|f| f.writeBytes("x") }
System.print(Directory.exists("sub"))
System.print(Directory.list("sub").count)
File.delete("sub/only.txt")
Directory.delete("sub")
System.print(Directory.exists("sub"))
EOF
out=$("$EXE" dirio.wren 2>/dev/null); rc=$?
eq 'directory roundtrip exits 0' '0' "$rc"
eq 'Directory.create + exists' 'true' "$(printf '%s' "$out" | sed -n '1p')"
eq 'Directory.list sees the created file' '1' "$(printf '%s' "$out" | sed -n '2p')"
eq 'Directory.delete 删空目录后 exists 为 false' 'false' "$(printf '%s' "$out" | sed -n '3p')"

# 上游 io.c 的 directoryDelete 走 uv_fs_rmdir + handleRequestError：删**非空**目录
# 抛运行期错误（真机实测 rc=70 = EX_SOFTWARE，stderr 首行是 uv_strerror 的
# "directory not empty"，后跟 scheduler/io/脚本 共 4 帧调用栈）。固化这个真实语义。
cat > dirnotempty.wren <<'EOF'
import "io" for Directory, File
Directory.create("sub2")
File.create("sub2/only.txt") {|f| f.writeBytes("x") }
Directory.delete("sub2")
EOF
err=$("$EXE" dirnotempty.wren 2>&1 >/dev/null); rc=$?
eq 'Directory.delete 删非空目录抛运行期错误 EX_SOFTWARE(70)' '70' "$rc"
eq '错误串取自 uv_strerror 且只报一次' '1' "$(printf '%s' "$err" | grep -c 'directory not empty')"
has '抛出的是带调用栈的运行期错误' 'in delete' "$err"
rm -rf sub2

cat > proc.wren <<'EOF'
import "os" for Platform, Process
System.print(Platform.isPosix)
System.print(Process.pid > 0)
System.print(Process.cwd)
System.print(Platform.homePath)
EOF
out=$("$EXE" proc.wren 2>/dev/null); rc=$?
eq 'os 模块运行退出码 0' '0' "$rc"
eq 'Platform.isPosix on OHOS' 'true' "$(printf '%s' "$out" | sed -n '1p')"
eq 'Process.pid is positive' 'true' "$(printf '%s' "$out" | sed -n '2p')"
eq 'Process.cwd matches the shell working directory' "$PHYS" "$(printf '%s' "$out" | sed -n '3p')"
if [ -n "${HOME:-}" ]; then
  eq 'Platform.homePath matches $HOME' "$HOME" "$(printf '%s' "$out" | sed -n '4p')"
else
  ne 'Platform.homePath is non-empty' '' "$(printf '%s' "$out" | sed -n '4p')"
fi

cat > sleep.wren <<'EOF'
import "timer" for Timer
System.print("1")
Timer.sleep(3)
System.print("2")
Timer.sleep(3)
System.print("3")
EOF
out=$("$EXE" sleep.wren 2>/dev/null); rc=$?
eq 'Timer.sleep run exits 0' '0' "$rc"
eq 'libuv timer resumes the main fiber in order' '1
2
3' "$out"

cat > stdin.wren <<'EOF'
import "io" for Stdin
System.print("got: %(Stdin.readLine())")
EOF
out=$(printf 'first\n' | "$EXE" stdin.wren 2>/dev/null); rc=$?
eq 'piped stdin run exits 0' '0' "$rc"
eq 'Stdin.readLine reads the piped line' 'got: first' "$out"

printf 'TOTAL=%s PASS=%s FAIL=%s\n' "$TOTAL" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
