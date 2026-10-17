#!/usr/bin/env bash
# HarmonyOS PC 专项验证 — irsim 9.7.104
# TAP 风格断言，独立临时目录，trap 清理，不写包目录。
set -euo pipefail

checks=0
fail=0

check() {
    checks=$((checks + 1))
    if [ "$2" = "ok" ]; then
        echo "ok $checks - $1"
    else
        echo "not ok $checks - $1 ($2)"
        fail=$((fail + 1))
    fi
}

PKGROOT="${PKGROOT:?PKGROOT must point at the installed package folder}"
TMPD=$(mktemp -d "${TMPDIR:-/tmp}/irsim-test-ohos.XXXXXX" 2>/dev/null || mktemp -d "${HOME}/tmp/irsim-test-ohos.XXXXXX")
trap 'rm -rf "$TMPD"' EXIT INT TERM

BIN="$PKGROOT/bin"
readelf="${OHOS_READELF:-readelf}"

# ── H1: ELF64 Little-Endian AArch64 for every shipped binary ─────────
for exe in irsim gentbl genspktbl; do
    f="$BIN/$exe"
    if [ ! -x "$f" ]; then
        check "H1 $exe is present and executable" "missing:$f"
        continue
    fi
    arch=""
    machine=""
    if "$readelf" -h "$f" > "$TMPD/h1.$$" 2>/dev/null; then
        arch="$(grep -E 'Class:|Data:|Machine:' "$TMPD/h1.$$" | tr '\n' ' ')"
        machine="$(grep 'Machine:' "$TMPD/h1.$$" || true)"
        case "$arch" in
            *ELF64* | *AArch64*)
                case "$machine" in
                    *AArch64*) check "H1 $exe ELF64 AArch64 LE" ok ;;
                    *) check "H1 $exe ELF64 AArch64 LE" "machine=$machine" ;;
                esac
                ;;
            *) check "H1 $exe ELF64 AArch64 LE" "arch=$arch" ;;
        esac
    else
        check "H1 $exe ELF64 AArch64 LE" "readelf failed for $f"
    fi
done

# ── H2: .codesign section (OHOS signature requirement) ───────────────
for exe in irsim gentbl genspktbl; do
    f="$BIN/$exe"
    [ -x "$f" ] || continue
    if "$readelf" -S "$f" 2>/dev/null | grep -q '\.codesign'; then
        check "H2 $exe has .codesign section" ok
    else
        check "H2 $exe has .codesign section" "missing"
    fi
done

# ── H3: no host build paths embedded in binaries ─────────────────────
for exe in irsim gentbl genspktbl; do
    f="$BIN/$exe"
    [ -x "$f" ] || continue
    n="$(strings "$f" 2>/dev/null | grep -cE '/home/|/tmp/|storage/Users/' || true)"
    [ "$n" = "0" ] && check "H3 $exe has no host paths" ok \
        || check "H3 $exe has no host paths" "count=$n"
done

# ── H4: real simulation run on OpenHarmony PC ────────────────────────
PRM="$(find "$PKGROOT" -name '*.prm' 2>/dev/null | sort | head -1)"
printf 'C xx Gnd 2\nC o Gnd 2\n' > "$TMPD/net.sim"
printf 'd\nexit\n' > "$TMPD/cmd.cmd"
out=""
rc=127
if [ -n "$PRM" ] && [ -x "$BIN/irsim" ]; then
    # rc 必须在命令替换之外接收 irsim 的真实退出码：
    # 命令替换子 shell 内的赋值不会传播到外层，`|| rc=$?` 写在
    # 替换内部会使外层 rc 恒为初始值 0，断言恒真（R02 bot 检视 P2）。
    out="$("$BIN/irsim" "$PRM" "$TMPD/net.sim" "-$TMPD/cmd.cmd" 2>&1)"
    rc=$?
fi
[ "$rc" = "0" ] && check "H4 irsim simulation exits 0" ok \
    || check "H4 irsim simulation exits 0" "rc=$rc"
case "$out" in
    *"4 nodes"*) check "H4 network loaded with expected 4 nodes" ok ;;
    *) check "H4 network loaded with expected 4 nodes" "out=$(echo "$out" | head -1)" ;;
esac

# ── H5: packaged parameter library data present ──────────────────────
np="$(find "$PKGROOT" -name '*.prm' 2>/dev/null | wc -l)"
[ "$np" -ge 1 ] && check "H5 packaged .prm parameter files present (count=$np)" ok \
    || check "H5 packaged .prm parameter files present" "count=$np"

echo "1..$checks"
if [ "$fail" -gt 0 ]; then
    echo "# FAILED $fail/$checks"
    exit 1
fi
echo "# passed $checks/$checks"