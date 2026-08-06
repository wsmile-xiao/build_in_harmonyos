#!/bin/sh
set -eu
set -o pipefail

# OHOS SELinux denies execution of any ELF on the hmdfs label that the Conan
# cache and $HOME carry, and exposes no writable+executable partition to the
# CI account. The recipe's test() therefore short-circuits on OHOS with
# compile-time assertions over the packaged artifacts and never calls this
# script there. This guard keeps the script safe if invoked directly on OHOS.
if [ -n "${OHOS:-}" ] || uname -r 2>/dev/null | grep -qi 'ohos'; then
  echo "openssh-ssh1 SSH1 functional tests skipped on OHOS (no writable+executable partition)"
  exit 0
fi

BIN_DIR="${1:-}"
test -n "$BIN_DIR"

SSH="$BIN_DIR/bin/ssh"
KEYGEN="$BIN_DIR/bin/ssh-keygen"
test -x "$SSH"
test -x "$KEYGEN"

"$SSH" -V 2>&1 | grep -q 'OpenSSH_7.5p1'
"$SSH" -1 -G localhost >/dev/null 2>&1

tmp_dir="${TMPDIR:-/tmp}/openssh-ssh1-test-$$"
mkdir -p "$tmp_dir"
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM
"$KEYGEN" -q -t rsa1 -N "" -f "$tmp_dir/id_rsa1"
test -s "$tmp_dir/id_rsa1"
test -s "$tmp_dir/id_rsa1.pub"

echo "openssh-ssh1 SSH1 functional tests passed"
