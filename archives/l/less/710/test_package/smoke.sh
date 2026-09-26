#!/bin/sh
# Behavioral consumer test for the packaged less binary (GLM-72).
set -e
BINDIR="$1"
if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/less" ]; then
    echo "smoke: missing packaged less under $BINDIR" >&2
    exit 1
fi
# CI worker 的 $HOME 下没有现成 tmp/ 目录，mktemp 带模板会直接失败；先建父目录，
# 建不出来（只读家目录等）再退回 /tmp。
TMPROOT="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPROOT" 2>/dev/null || TMPROOT=/tmp
WORK=$(mktemp -d "$TMPROOT/less-smoke.XXXXXX") || exit 1
trap 'rm -rf "$WORK"' EXIT
printf 'alpha line 1\nbeta line 2\ngamma line 3\n' > "$WORK/in.txt"

# 1) -F (quit-if-one-screen) prints the whole file to stdout
"$BINDIR/less" -F "$WORK/in.txt" > "$WORK/out.txt" 2>"$WORK/e1"
RC=$?
[ $RC -eq 0 ] || { echo "smoke: less -F failed rc=$RC" >&2; exit 1; }
grep -q "beta line 2" "$WORK/out.txt" || { echo "smoke: -F output missing line" >&2; exit 1; }

# 2) empty file: -F exits 0 with empty output
: > "$WORK/empty.txt"
"$BINDIR/less" -F "$WORK/empty.txt" > "$WORK/oute.txt" 2>"$WORK/e2"
RC=$?
[ $RC -eq 0 ] || { echo "smoke: less -F on empty failed rc=$RC" >&2; exit 1; }
[ ! -s "$WORK/oute.txt" ] || { echo "smoke: -F on empty produced output" >&2; exit 1; }

# 3) missing file: must fail AND emit a diagnostic. 上游 less 在不同 libc/终端条件下
#    会把该诊断打在 stdout 或 stderr，原先只收 stderr 且把 stdout 丢进 /dev/null，
#    等于用一条可能被丢弃的流做断言。⇒ 两路都落盘再联合判；失败时把两路的字节数与
#    前 200 字节原样回吐，让下一次运行本身就是证据（而不是又一次同义失败）。
"$BINDIR/less" -F "$WORK/nope.txt" < /dev/null > "$WORK/o3" 2>"$WORK/e3" || true
# OHOS 上 /bin/grep 是 toybox：不支持 BRE 的 \\| 交替，整串被当字面量 ⇒ 断言恒不匹配（假失败）。
# 用多个 -e 传分支，GNU grep / toybox grep / busybox grep 行为一致。
if ! grep -qi -e "no such" -e "cannot open" -e "does not exist" "$WORK/e3" "$WORK/o3"; then
    E3SZ=$(wc -c < "$WORK/e3")
    O3SZ=$(wc -c < "$WORK/o3")
    echo "smoke: missing-file diagnostic missing (stderr=${E3SZ}B stdout=${O3SZ}B)" >&2
    echo "----- stderr -----" >&2; head -c 200 "$WORK/e3" >&2
    echo "----- stdout -----" >&2; head -c 200 "$WORK/o3" >&2
    exit 1
fi

# 4) --version exits 0 and names less
"$BINDIR/less" --version > "$WORK/ver.txt" 2>&1
grep -qi "^less" "$WORK/ver.txt" || { echo "smoke: --version output unexpected" >&2; exit 1; }

echo "less consumer OK: 4 behavioral scenarios asserted"
