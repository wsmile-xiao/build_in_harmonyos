#!/system/bin/sh
set -eu

if [ -z "${ACONF_OPENSSH_MODULE:-}" ]; then
    echo "FAIL: ACONF_OPENSSH_MODULE not set"
    exit 1
fi

if [ ! -f "$ACONF_OPENSSH_MODULE" ]; then
    echo "FAIL: openssh.lua not found: $ACONF_OPENSSH_MODULE"
    exit 1
fi

echo "PASS: openssh.lua exists"

if ! grep -q "aconf.model" "$ACONF_OPENSSH_MODULE"; then
    echo "FAIL: openssh.lua does not reference aconf.model"
    exit 1
fi

echo "PASS: openssh.lua references aconf.model"
echo "All 2 tests passed."
