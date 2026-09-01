#!/usr/bin/env bash
# R34: real smoke test for aurpublish 20231227.3b978be — exercises the
# packaged script. aurpublish is a bash script, so we run it with `bash`
# (OHOS has no /bin/bash interpreter path; the script keeps its upstream
# shebang for standard Linux systems).
#
# Checks:
#   1. script installed and executable
#   2. bash syntax check
#   3. `aurpublish --help` exits 0 and prints the usage text
#   4. `aurpublish setup` inside a scratch git repository installs the
#      3 git hooks from the package share/ layout (proves the runtime
#      HOOKSDIR resolution of the rendered script)
set -u

BIN_DIR="${1:?usage: test_aurpublish.sh <package bin dir>}"
AURPUBLISH="$BIN_DIR/aurpublish"

fail() {
    echo "FAIL: $1"
    exit 1
}

# 1. presence + executable bit
[ -x "$AURPUBLISH" ] || fail "aurpublish missing or not executable in $BIN_DIR"

# 2. bash syntax
bash -n "$AURPUBLISH" || fail "bash syntax check failed"

# 3. real CLI execution: --help must exit 0 and print usage
out="$(bash "$AURPUBLISH" --help)" || fail "--help exited non-zero"
echo "$out" | grep -q "Usage: aurpublish" || fail "usage text missing in --help output"
echo "$out" | grep -q "Push a subtree to the AUR" || fail "description text missing in --help output"

# 4. setup subcommand in a scratch git repo: hooks must be installed from
#    the package layout (validates HOOKSDIR runtime resolution)
TESTREPO="$(mktemp -d)"
trap 'rm -rf "$TESTREPO"' EXIT
git -C "$TESTREPO" init -q || fail "git init failed"
git -C "$TESTREPO" config user.email test@local.invalid
git -C "$TESTREPO" config user.name "conan test"
echo hello > "$TESTREPO/README.md"
git -C "$TESTREPO" add README.md
git -C "$TESTREPO" commit -qm "init" || fail "git commit failed"

setup_out="$(cd "$TESTREPO" && bash "$AURPUBLISH" setup)" \
    || fail "setup exited non-zero"
echo "$setup_out" | grep -q "Adding commit hooks" || fail "setup output unexpected"
for h in pre-commit post-commit prepare-commit-msg; do
    [ -e "$TESTREPO/.git/hooks/$h" ] || fail "hook $h not installed by setup"
done

echo "aurpublish smoke test: OK (help + syntax + setup/hooks)"
exit 0
