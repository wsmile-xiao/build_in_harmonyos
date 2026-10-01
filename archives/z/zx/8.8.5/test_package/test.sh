#!/bin/sh
# test_package/test.sh — consumer smoke test for the packaged zx CLI.
#
# Mirrors test_package/conanfile.py: really executes the packaged bin/zx
# launcher (R34 — not a stub), so the CI L1e destructive negative test can
# move bin/ away and observe the failure.
#
# Usage: sh test.sh [path-to-bin/zx]
set -eu

BIN="${1:-zx}"
TMPDIR="${TMPDIR:-/storage/Users/currentUser/tmp}"
export TMPDIR
mkdir -p "$TMPDIR" 2>/dev/null || true

# Run from an explicit existing directory: a child process started in a deleted
# cwd fails with "shell-init: error retrieving current directory: getcwd: ..."
# (measured under `conan test`, which may delete its temporary build folder).
WORKDIR="$TMPDIR/zx-test-package-sh"
rm -rf "$WORKDIR"; mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "[test] $BIN --version"
out="$("$BIN" --version 2>&1)" || {
    echo "❌ $BIN --version failed (exit=$?)"
    exit 1
}
echo "$out"
case "$out" in
    *8.8.5*) echo "✅ --version reports 8.8.5" ;;
    *) echo "❌ --version did not report 8.8.5"; exit 1 ;;
esac

echo "[test] $BIN -e (real \$ command capture)"
out2="$("$BIN" -e 'const o = await $`echo zx-consumer-ok`; console.log(o.stdout.trim().toUpperCase())' 2>&1)" || {
    echo "❌ $BIN -e failed (exit=$?)"
    exit 1
}
echo "$out2"
case "$out2" in
    *ZX-CONSUMER-OK*) echo "✅ \$ command capture works" ;;
    *) echo "❌ command capture broken"; exit 1 ;;
esac

echo "[test] $BIN script file (fs/\$)"
cat > "$WORKDIR/consumer.mjs" <<'EOF'
#!/usr/bin/env zx
const dir = path.join(os.tmpdir(), 'zx-consumer-work-sh')
await $`mkdir -p ${dir}`
const listed = (await $`ls -d ${dir}`).stdout.trim()
fs.writeFileSync(path.join(dir, 'probe.txt'), 'zx-consumer')
const content = (await $`cat ${path.join(dir, 'probe.txt')}`).stdout.trim()
fs.removeSync(dir)
console.log('LS=' + listed)
console.log('CONTENT=' + content)
EOF
out3="$("$BIN" "$WORKDIR/consumer.mjs" 2>&1)" || {
    echo "❌ script file execution failed (exit=$?)"
    exit 1
}
echo "$out3"
case "$out3" in
    *CONTENT=zx-consumer*) echo "✅ script file execution works" ;;
    *) echo "❌ script file execution broken"; exit 1 ;;
esac

echo "[test] $BIN - (stdin script)"
out4="$(printf "console.log('STDIN_OK')\n" | "$BIN" - 2>&1)" || {
    echo "❌ stdin script failed (exit=$?)"
    exit 1
}
echo "$out4"
case "$out4" in
    *STDIN_OK*) echo "✅ stdin script works" ;;
    *) echo "❌ stdin script broken"; exit 1 ;;
esac

rm -rf "$WORKDIR"
echo "zx test_package: 4/4 checks passed"
exit 0
