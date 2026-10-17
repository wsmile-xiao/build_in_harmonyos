#!/usr/bin/env bash
# test.sh — smoke test for nuget package
# Verifies NuGet.exe binary integrity without executing it (PE32 binary, needs .NET runtime)

set -e

NUGET_LIBEXEC="${1:-libexec}"
NUGET_EXE="${NUGET_LIBEXEC}/NuGet.exe"

echo "=== Running nuget package smoke test ==="

# 1. Verify NuGet.exe exists
if [ ! -f "$NUGET_EXE" ]; then
    echo "FAIL: NuGet.exe not found at $NUGET_EXE"
    exit 1
fi
echo "PASS: NuGet.exe found at $NUGET_EXE"

# 2. Verify PE32 header (MZ magic bytes)
if ! head -c 2 "$NUGET_EXE" | grep -q "MZ"; then
    echo "FAIL: NuGet.exe does not have MZ PE header"
    exit 1
fi
echo "PASS: NuGet.exe has valid MZ PE header"

# 3. Verify file size (> 1MB, expected ~8MB)
FILE_SIZE=$(stat -c%s "$NUGET_EXE" 2>/dev/null || stat -f%z "$NUGET_EXE")
if [ "$FILE_SIZE" -lt 1000000 ]; then
    echo "FAIL: NuGet.exe too small ($FILE_SIZE bytes)"
    exit 1
fi
echo "PASS: NuGet.exe size OK ($FILE_SIZE bytes)"

# 4. Verify wrapper script exists
NUGET_WRAPPER="$(dirname "$NUGET_LIBEXEC")/bin/nuget"
if [ ! -f "$NUGET_WRAPPER" ]; then
    echo "FAIL: nuget wrapper not found at $NUGET_WRAPPER"
    exit 1
fi
echo "PASS: nuget wrapper found"

# 5. Verify NOTICES.txt exists
NOTICES="$(dirname "$NUGET_LIBEXEC")/share/NOTICES.txt"
if [ ! -f "$NOTICES" ]; then
    echo "FAIL: NOTICES.txt not found at $NOTICES"
    exit 1
fi
echo "PASS: NOTICES.txt found"

echo "=== All nuget smoke tests passed ==="
exit 0
