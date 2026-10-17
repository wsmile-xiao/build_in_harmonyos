#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer-side verification of the packaged runawk.
# Runs inside the conanrun environment, so bin/runawk and the mawk
# interpreter (runawk's runtime dependency) are both on PATH.
set -eu

# HarmonyOS: the Electron CLI vendor "safe-bin" shim directory ships a broken
# `rm` (dangling symlink) that shadows the working one; strip it so cleanup
# (rm -rf in the EXIT trap) does not fail.
case ":$PATH:" in
  *":safe-bin:"*) PATH=$(echo "$PATH" | tr ':' '\n' | grep -v 'safe-bin' | paste -sd: -) ;;
esac

echo "[test] runawk is on PATH"
command -v runawk
echo "[test] awk interpreter from the mawk dependency is on PATH"
command -v mawk

workdir="${TMPDIR:-$PWD}/runawk-test-$$"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"
cd "$workdir"
export TMPDIR="$workdir/tmp"
mkdir -p "$TMPDIR"

echo "[test] runawk -V"
runawk -V | head -1

echo "[test] inline program"
out=$(runawk -e 'BEGIN {print "hello from runawk"}')
test "$out" = "hello from runawk"

echo "[test] pipeline usage (runawk ... 2>&1 | ...), the normal shell idiom"
out=$(runawk -e 'BEGIN {print "piped"}' 2>&1 | sed -n '1p')
test "$out" = "piped"

echo "[test] stdin driven program"
out=$(printf 'one two three\n' | runawk -e '{print $2}')
test "$out" = "two"

echo "[test] bundled module through MODULESDIR (abs/min/max)"
cat > prog.awk <<'EOF'
#use "abs.awk"
#use "min.awk"
#use "max.awk"
BEGIN {
    print abs(-42)
    print min(3, 7)
    print max(3, 7)
    exit
}
EOF
out=$(runawk prog.awk)
expected=$'42\n3\n7'
test "$out" = "$expected"

echo "[test] consumer script using the shquote module"
cat > consumer.awk <<'EOF'
#use "shquote.awk"
BEGIN {
    print shquote("/data/local/tmp/a b.txt")
    exit
}
EOF
out=$(runawk consumer.awk)
test "$out" = "'/data/local/tmp/a b.txt'"

echo "[test] alt_getopt companion script is installed"
command -v alt_getopt

echo "[test] OHOS: packaged launcher is an ELF64 aarch64 executable"
binary=$(command -v runawk)
magic=$(od -An -tx1 -N6 "$binary" | tr -d ' \n')
test "$magic" = "7f454c460201"
machine=$(od -An -tu1 -j18 -N2 "$binary" | awk '{print $1 + $2 * 256}')
test "$machine" = "183"

echo "[test] OHOS: module run succeeds even though /tmp is read-only"
if [ -w /tmp ]; then
    echo "[test] note: /tmp writable here, fallback not exercised"
else
    runawk prog.awk > /dev/null
    echo "[test] ok: generated program went to TMPDIR=$TMPDIR"
fi

echo "[test] all assertions passed"
