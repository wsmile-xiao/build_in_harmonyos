#!/bin/sh
# R34: real smoke test for rumur — exercises the packaged CLI artifact.
#
# rumur is a Murphi model checker: it translates a `.m` model into a C
# verifier. The checks below cover the packaged binary itself, the ordinary
# compile-to-/dev/null consumer case, and the OHOS-specific
# compile-to-/dev/stdout case that the recipe patch fixes (/dev/stdout is a
# symlink to /proc/self/fd/1 on OHOS and cannot be re-opened).
#
# usage: test_rumur.sh <rumur binary> <model.m>
set -u

BIN="${1:?usage: test_rumur.sh <rumur binary> <model.m>}"
MODEL="${2:?usage: test_rumur.sh <rumur binary> <model.m>}"

FAIL=0

fail() {
    echo "FAIL: $1"
    FAIL=1
}

# --- 1. the packaged artifact is present and executable ---------------------
if [ ! -x "$BIN" ]; then
    fail "$BIN missing or not executable"
fi
if [ ! -f "$MODEL" ]; then
    fail "model fixture missing: $MODEL"
fi

if [ "$FAIL" -eq 0 ]; then
    # --- 2. the binary executes and links (--version) -----------------------
    VER=$("$BIN" --version 2>&1) || fail "rumur --version exited non-zero"
    echo "  [ok] rumur --version -> $VER"

    # --- 3. consumer case: compile the model, discard the verifier ---------
    if "$BIN" --output=/dev/null "$MODEL"; then
        echo "  [ok] rumur --output=/dev/null $MODEL"
    else
        fail "rumur --output=/dev/null $MODEL exited non-zero"
    fi

    # --- 4. OHOS-specific: regenerate the verifier onto stdout -------------
    # On OHOS /dev/stdout is a symlink to /proc/self/fd/1 and opening it fails
    # with ENOENT, so an unpatched rumur aborts here. This is the exact
    # invocation used by the upstream `rumur-run` wrapper
    # (rumur/src/rumur-run: `--output /dev/stdout`), and the recipe patch makes
    # it fall back to the already-open std::cout. Command substitution keeps
    # fd 1 a pipe, so the check cannot accidentally pass just because stdout
    # happened to be a re-openable regular file.
    #
    # The verifier is ~4.7k lines; assert on it with a shell pattern rather
    # than piping it through an external tool, because OHOS /system/bin/printf
    # rejects an argument that large with E2BIG ("Argument list too long").
    C=$("$BIN" --output=/dev/stdout "$MODEL") || fail "rumur --output=/dev/stdout $MODEL exited non-zero"
    case "$C" in
        "")
            fail "rumur --output=/dev/stdout produced no output"
            ;;
        *"int main"*)
            echo "  [ok] rumur --output=/dev/stdout -> generated verifier emitted on stdout"
            ;;
        *)
            fail "rumur --output=/dev/stdout did not emit a verifier (no 'int main' found)"
            ;;
    esac
fi

if [ "$FAIL" -eq 0 ]; then
    echo "rumur smoke test: OK"
fi
exit "$FAIL"
