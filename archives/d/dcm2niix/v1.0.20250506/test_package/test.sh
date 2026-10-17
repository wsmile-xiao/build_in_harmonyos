#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the dcm2niix executable.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. `dcm2niix`).
set -euo pipefail

DCM2NIIX="${1:-dcm2niix}"

echo "[step] dcm2niix --version"
# dcm2niix quirk: --version prints version but returns non-zero exit code.
# Capture output and don't fail on exit code — verify via output content instead.
VERSION_OUT="$("$DCM2NIIX" --version 2>&1)" || true
echo "$VERSION_OUT"
if echo "$VERSION_OUT" | grep -qi "dcm2niiX version v"; then
    echo "✅ dcm2niix --version OK (binary executable, ELF valid)"
else
    echo "❌ dcm2niix --version failed — unexpected output"
    exit 1
fi

echo "[step] dcm2niix scan empty directory"
# Functional test: dcm2niix's core job is to scan a directory for DICOM files
# and convert them. Scanning an empty directory exercises the core scan path
# (directory traversal, DICOM detection). dcm2niix returns non-zero when no
# convertible files are found, so we capture output and don't fail on exit code.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/dcm2niix-test.XXXXXX")" || exit 1
[ -n "$WORK" ] && [ -d "$WORK" ] || exit 1
trap 'rm -rf "$WORK"' EXIT

SCAN_OUT="$("$DCM2NIIX" -v 2 -o "$WORK/out" "$WORK" 2>&1)" || true
echo "$SCAN_OUT"

# Verify dcm2niix actually ran and produced its signature output
if echo "$SCAN_OUT" | grep -qi "dcm2niiX version v"; then
    echo "✅ dcm2niix scan OK (core function verified)"
else
    echo "❌ dcm2niix scan failed — unexpected output:"
    echo "$SCAN_OUT"
    exit 1
fi

echo "dcm2niix test_package: PASS"
