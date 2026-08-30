#!/bin/sh
# Note: uses POSIX /bin/sh (with set -eu) instead of zsh because the OHOS
# build environment provides /system/bin/sh; no bash/zsh-specific features
# are used so the assertions are portable across shells.
set -eu

BIN="$1"
DNS_BIN="$2"

VERSION_OUTPUT="$("$BIN" --version)"
echo "$VERSION_OUTPUT"
echo "$VERSION_OUTPUT" | grep -F "1.0.0"

HELP_OUTPUT="$("$BIN" --help)"
echo "$HELP_OUTPUT"
echo "$HELP_OUTPUT" | grep -F "usage"
echo "$HELP_OUTPUT" | grep -F "SOCKS5"

DNS_HELP_OUTPUT="$("$DNS_BIN" --help)"
echo "$DNS_HELP_OUTPUT"
echo "$DNS_HELP_OUTPUT" | grep -F "usage"
