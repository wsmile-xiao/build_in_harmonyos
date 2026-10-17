#!/bin/sh
# pre-build.sh for unixodbc 2.3.12
# Manual helper matching the current Conan recipe. The preferred source is the
# release tarball, which already contains configure; this script only applies
# the checked-in OHOS temporary-directory patch.

set -e

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
PATCH_FILE=${1:-"$SCRIPT_DIR/../patches/0007-ohos-umask-tmpdir.patch"}

echo "=== pre-build.sh: unixODBC 2.3.12 release-tarball preparation ==="

if [ ! -f configure ] || [ ! -f libltdl/configure ]; then
    echo "ERROR: configure files are missing. Use the unixODBC 2.3.12 release tarball." >&2
    exit 1
fi

if git apply --reverse --check "$PATCH_FILE" >/dev/null 2>&1; then
    echo "=== OHOS umask patch is already applied ==="
elif git apply --check "$PATCH_FILE"; then
    echo "=== Applying OHOS umask patch ==="
    git apply "$PATCH_FILE"
else
    echo "ERROR: OHOS umask patch cannot be applied cleanly: $PATCH_FILE" >&2
    exit 1
fi

echo "=== pre-build.sh completed ==="
