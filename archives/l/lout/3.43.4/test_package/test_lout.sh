#!/bin/sh
# Consumer + OHOS verification for lout/3.43.4.
# Invoked by test_package/conanfile.py test() via self.run() with env:
#   LOUT_BIN_DIR  - package bin/ absolute path
#   LOUT_LIB_DIR  - package res/lib absolute path (LOUTLIB tree)
#   TEST_SRC_DIR   - this test_package dir (contains hello.lout)
# Exit 0 = all checks passed.
set -u

fail() { echo "[FAIL] $1" >&2; exit 1; }

LOUT="$LOUT_BIN_DIR/lout"
PRG2LOUT="$LOUT_BIN_DIR/prg2lout"

# All lout outputs (PS/text files and cross-ref db *.ld/*.ldx/*.li, which
# land in cwd) must go to a throwaway dir — `conan test` without layout()
# runs with cwd = this source dir, so writing to $PWD would pollute the
# tree. cd into the scratch dir to contain everything; cleaned on exit.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/lout-test.XXXXXX")" || fail "mktemp failed"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || fail "cannot cd into scratch dir"

[ -x "$LOUT" ]     || fail "lout binary missing/not executable"
[ -x "$PRG2LOUT" ] || fail "prg2lout binary missing/not executable"

# ── 1. smoke ────────────────────────────────────────────────────
"$LOUT" --version || fail "lout --version"
"$LOUT" --version | grep -q "3.43" || fail "unexpected version banner"

# prg2lout reads stdin when given no args — feed EOF, expect usage exit
</dev/null "$PRG2LOUT" >/dev/null 2>&1
rc=$?
[ "$rc" -lt 128 ]  || fail "prg2lout crashed (rc=$rc)"

# ── 2. functional: real document formatting via the package tree ──
[ -d "$LOUT_LIB_DIR/data" ] || fail "res/lib/data missing"
export LOUTLIB="$LOUT_LIB_DIR"

# The cross-ref database is written next to the INPUT file (path stem +
# .ld/.ldx/.li, see z33.c DbLoad), not to cwd — so copy hello.lout into
# WORK and reference it by bare name, matching upstream `make test` which
# runs `./lout -r3 all -o user.ps` from inside doc/user.
cp "$TEST_SRC_DIR/hello.lout" "$WORK/hello.lout" || fail "cp hello.lout"
"$LOUT" hello.lout -o "$WORK/hello.ps" \
    || fail "PS formatting run failed"
head -c 4 "$WORK/hello.ps" | grep -q "%!PS" || fail "output is not PostScript"
[ -s "$WORK/hello.ps" ] || fail "hello.ps empty"

"$LOUT" -p hello.lout -o "$WORK/hello.txt" \
    || fail "plain-text formatting run failed"
grep -q "hello" "$WORK/hello.txt" || fail "plain text missing content"

# ── 3. OHOS-specific checks ─────────────────────────────────────
# 3a. ELF: aarch64 + musl interpreter
file_out=$(file "$LOUT")
echo "$file_out" | grep -q "ELF"  || fail "not an ELF binary"
echo "$file_out" | grep -qi "arm64" || fail "not an aarch64 ELF"
readelf -l "$LOUT" | grep -q "/ld-musl-aarch64" || fail "musl interpreter not found"

# 3b. hardening: RELRO + NX stack
rel=$(readelf -lW "$LOUT")
echo "$rel" | grep -q "GNU_RELRO" || fail "no GNU_RELRO segment"
stack=$(echo "$rel" | awk '/GNU_STACK/{print $7}')
[ "$stack" = "RW" ] || fail "GNU_STACK is not NX (flags=$stack)"

# 3c. dynamic deps: musl libc only (POSIX grep -e, no \| alternation)
bad=$(readelf -d "$LOUT" | grep NEEDED | grep -v -e "libc\.so" -e "ld-musl")
[ -z "$bad" ] || fail "unexpected dynamic deps: $bad"

# 3d. runtime regression guard: bad input must fail gracefully (no
#     signal) — guards the catgets (nl_catd)-1 sentinel fix (patch 0001)
"$LOUT" "$WORK/nonexistent.lout" -o "$WORK/x.ps" >/dev/null 2>&1
rc=$?
[ "$rc" -gt 0 ]    || fail "missing input must fail"
[ "$rc" -lt 128 ]  || fail "lout crashed on bad input (rc=$rc) — patch 0001 regression"

echo "[ok] lout consumer + OHOS checks passed"
