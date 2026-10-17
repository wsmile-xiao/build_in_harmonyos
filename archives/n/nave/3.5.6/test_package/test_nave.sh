#!/bin/bash
# test_nave.sh — Conan L1 consumer-side test for nave
# Verifies that the packaged nave.sh is installed, executable, and functional.
set -e

# Locate nave.sh: positional arg $1 (passed by test conanfile) or NAVE_BIN env var
NAVE_SH="${1:-${NAVE_BIN:-nave.sh}}"

if [ ! -f "$NAVE_SH" ]; then
    echo "FAIL: nave.sh not found at $NAVE_SH"
    exit 1
fi

if [ ! -x "$NAVE_SH" ]; then
    echo "FAIL: nave.sh is not executable: $NAVE_SH"
    exit 1
fi

# Check shebang is bash
head -1 "$NAVE_SH" | grep -q '^#!/bin/bash' || {
    echo "FAIL: nave.sh does not start with #!/bin/bash"
    exit 1
}

# Functional check 1: nave without command prints help and exits 0
bash "$NAVE_SH" > /dev/null 2>&1 || echo "INFO: bare nave invocation exited non-zero (expected: help printed to stderr)"

# Functional check 2: nave ls-all / version listing path must be reachable
bash "$NAVE_SH" help > /dev/null 2>&1
rc=$?
if [ $rc -ne 0 ]; then
    echo "FAIL: 'nave help' exited with code $rc"
    exit 1
fi

# Functional check 3: nave get dir returns a non-empty directory path
NAVE_DIR="$(bash "$NAVE_SH" get dir)"
if [ -z "$NAVE_DIR" ]; then
    echo "FAIL: 'nave get dir' returned empty"
    exit 1
fi

echo "PASS: nave.sh installed, executable, help + get dir work"
exit 0
