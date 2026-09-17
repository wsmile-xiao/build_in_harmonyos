#!/bin/sh
set -eu

probe=""
if [ -n "${CHRPATH_PROBE:-}" ] && [ -f "${CHRPATH_PROBE}" ]; then
    probe=${CHRPATH_PROBE}
else
    probe=$(find . -type f -name chrpath_rpath_probe -print -quit)
fi
if [ -z "${probe}" ] || [ ! -f "${probe}" ]; then
    echo "HarmonyOS RPATH probe was not built locally" >&2
    exit 1
fi

# Leave the shared consumer probe in its original state for test.sh, which
# intentionally starts by listing the old RPATH and then exercises deletion.
trap 'chrpath --replace /data/local/tmp/chrpath-ohos-old "${probe}" >/dev/null 2>&1 || true' EXIT

# The package and this AArch64 probe are both built on the HarmonyOS target,
# so no prebuilt ELF is transferred from the host.  The /data/local/tmp path
# exercises the target-specific long-option and ELF RPATH behavior.
chrpath --replace /data/local/tmp/chrpath-ohos-new "${probe}"
chrpath --list "${probe}" | grep -F '/data/local/tmp/chrpath-ohos-new' >/dev/null

echo "HarmonyOS chrpath RPATH test passed"
