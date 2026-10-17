#!/usr/bin/env bash
# leaf-md 1.26.1 consumer test suite.
#
# Executed by test_package/conanfile.py against the *installed* artefact.
#
#   Group A 消费者测试   — the packaged `leaf` binary driven through its public
#                          CLI exactly as an end user would (version/help
#                          contract, Markdown rendering from a file and from a
#                          stdin pipe, unknown-option error handling).
#   Group B 鸿蒙特有测试 — the packaged ELF checked against HarmonyOS PC
#                          runtime constraints (AArch64 machine, HarmonyOS
#                          signature, OHOS-native libc/interpreter).
#
# Exit code 0 = every check passed, 1 = at least one check failed.

set -uo pipefail

BIN="${LEAF_BIN:?LEAF_BIN must point at the packaged leaf binary}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${PYTHON:-python3}"

pass=0
fail=0

pass_check() { echo "  [PASS] $1"; pass=$((pass + 1)); }

fail_check() { # fail_check <name> <detail...>
    echo "  [FAIL] $1"
    shift
    for line in "$@"; do echo "         $line"; done
    fail=$((fail + 1))
}

expect_contains() { # expect_contains <name> <needle> <haystack>
    if printf '%s' "$3" | grep -qF -- "$2"; then
        pass_check "$1"
    else
        fail_check "$1" \
            "expected to contain: $2" \
            "actual: $(printf '%s' "$3" | head -c 400)"
    fi
}

expect_rc() { # expect_rc <name> <expected-rc> <actual-rc>
    if [ "$3" = "$2" ]; then
        pass_check "$1"
    else
        fail_check "$1" "expected exit code $2, got $3"
    fi
}

echo "== Group A: consumer tests (installed binary driven via its CLI) =="
echo "   binary: $BIN"

# A1 — version contract.
out="$("$BIN" --version 2>&1)"
expect_contains "A1 leaf --version reports upstream version" "leaf 1.26.1" "$out"

# A2 — help contract (a consumer must be able to discover the CLI).
out="$("$BIN" --help 2>&1)"
rc=$?
expect_rc "A2 leaf --help exits 0" 0 "$rc"
expect_contains "A2 leaf --help lists usage" "Usage:" "$out"

# A3 — render a Markdown file to stdout (headless rendering path).
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cat > "$work/doc.md" <<'MD'
# Leaf HarmonyOS

A **bold** statement with [a link](https://example.com).

- alpha
- beta

```rust
let platform = "ohos";
```
MD
out="$("$BIN" --inline plain "$work/doc.md" 2>&1)"
rc=$?
expect_rc "A3 leaf --inline plain <file> exits 0" 0 "$rc"
expect_contains "A3 renders heading text" "Leaf HarmonyOS" "$out"
expect_contains "A3 renders list item" "alpha" "$out"
expect_contains "A3 renders fenced code block" "let platform" "$out"

# A4 — render from a stdin pipe (the shell-integration path).
out="$(printf '# Piped Heading\n\nbody text\n' | "$BIN" --inline plain 2>&1)"
rc=$?
expect_rc "A4 leaf --inline plain via stdin pipe exits 0" 0 "$rc"
expect_contains "A4 renders piped Markdown" "Piped Heading" "$out"

# A5 — an unknown option must be rejected, not silently ignored.
"$BIN" --definitely-not-an-option > /dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    pass_check "A5 unknown option rejected with non-zero exit ($rc)"
else
    fail_check "A5 unknown option rejected with non-zero exit" "exit code was 0"
fi

echo "== Group B: HarmonyOS-specific tests (packaged ELF vs OHOS runtime) =="
if "$PY" "$SCRIPT_DIR/ohos_elf_check.py" "$BIN"; then
    pass=$((pass + 3))
else
    fail=$((fail + 3))
fi

echo
echo "leaf-md consumer suite: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
exit 0
