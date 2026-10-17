#!/data/service/hnp/bin/bash
set -euo pipefail

echo "[test] ssmtp -V"
ssmtp -V && echo "OK: ssmtp -V succeeded" || {
    echo "[test] -V failed, trying --help..."
    ssmtp --help > /dev/null 2>&1 && echo "OK: --help succeeded" || {
        echo "FAIL: ssmtp failed both -V and --help"
        exit 1
    }
}

echo "[test] SSL support (STARTTLS present in binary)"
# Strip NUL bytes before grep: toybox grep (first on PATH in the CI test
# environment) does not match patterns in files containing NUL bytes.
# Process substitution instead of a pipeline: grep -q exits on first match,
# tr would die of SIGPIPE and "set -o pipefail" would fail the check.
SSMTP_BIN="$(command -v ssmtp)"
if [ -n "$SSMTP_BIN" ] && grep -qa STARTTLS < <(tr -d '\0' < "$SSMTP_BIN"); then
    echo "OK: SSL/TLS support compiled in (STARTTLS marker found)"
else
    echo "FAIL: SSL/TLS support missing from binary"
    exit 1
fi
