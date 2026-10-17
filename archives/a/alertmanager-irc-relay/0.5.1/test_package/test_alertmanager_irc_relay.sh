#!/usr/bin/env bash
# Smoke test for the installed alertmanager-irc-relay binary.
set -euo pipefail

TMP_HELP=""
TMP_OUT=""

cleanup() {
    # 安全清理临时文件：mktemp/被测命令/清理失败时脚本以非零退出（set -e）。
    if [ -n "$TMP_HELP" ] && [ -e "$TMP_HELP" ]; then
        rm -f -- "$TMP_HELP"
    fi
    if [ -n "$TMP_OUT" ] && [ -e "$TMP_OUT" ]; then
        rm -f -- "$TMP_OUT"
    fi
}
trap cleanup EXIT

if [ "$#" -lt 1 ]; then
    echo "[FAIL] usage: $0 <binary>"
    exit 1
fi
BIN="$1"

if [ ! -x "$BIN" ]; then
    echo "[FAIL] binary not executable: $BIN"
    exit 1
fi

# Scenario 1 (normal, no network): --help must print Go flag usage and exit 0.
# Verified on real OHOS: flag.Parse() handles --help, prints "Usage of ..."
# with the -config flag, and returns 0 without touching the network.
echo "[INFO] scenario 1: running $BIN --help (expecting usage text, exit 0)"
TMP_HELP="$(mktemp)"
set +e
timeout 15 "$BIN" --help >"$TMP_HELP" 2>&1
HELP_RC=$?
set -e
HELP_OUT="$(cat "$TMP_HELP")"
rm -f "$TMP_HELP"
if [ "$HELP_RC" -ne 0 ]; then
    echo "[FAIL] --help expected exit 0, got $HELP_RC — output: $HELP_OUT"
    exit 1
fi
case "$HELP_OUT" in
    *"Usage of"*)
        echo "[PASS] --help printed usage: exit=$HELP_RC, output matches"
        ;;
    *)
        echo "[FAIL] --help output did not contain 'Usage of'; got:"
        echo "$HELP_OUT"
        exit 1
        ;;
esac

# Scenario 2 (error path, no network): when the config file does not exist
# main() logs "Could not load config: ..." and returns (exit 0).  Running with
# no --config at all would block trying to connect to IRC, so we always pass
# an explicit (non-existent) config path.
echo "[INFO] scenario 2: running $BIN --config <nonexistent> (expecting config-load error)"
TMP_OUT="$(mktemp)"
set +e
timeout 30 "$BIN" --config /nonexistent/alertmanager-irc-relay-config.yml >"$TMP_OUT" 2>&1
RC=$?
set -e
OUTPUT="$(cat "$TMP_OUT")"
rm -f "$TMP_OUT"

# Verified on real OHOS: main() returns normally after logging the error, so
# exit code is 0 (not os.Exit).  The output must contain the expected error.
if [ "$RC" -ne 0 ]; then
    echo "[FAIL] expected exit 0, got $RC — output: $OUTPUT"
    exit 1
fi
case "$OUTPUT" in
    *"Could not load config"*)
        echo "[PASS] CLI reported config-load error: exit=$RC, output matches"
        ;;
    *)
        echo "[FAIL] output did not contain 'Could not load config'; got:"
        echo "$OUTPUT"
        exit 1
        ;;
esac
exit 0