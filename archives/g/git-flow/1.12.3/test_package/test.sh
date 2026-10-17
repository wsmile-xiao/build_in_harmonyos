#!/bin/sh
# test_package/test.sh — smoke test for git-flow 1.12.3
# CI L0c requires a test source file to exist alongside conanfile.py.
# The actual test logic is in conanfile.py's test() method which runs
# `git-flow version` and verifies the output.

echo "test.sh: git-flow smoke test placeholder"
#!/bin/sh
# test_package/test.sh — smoke test for git-flow 1.12.3

if command -v git-flow >/dev/null 2>&1; then
    git-flow version && echo "PASS: git-flow version OK"
else
    echo "FAIL: git-flow not found on PATH" >&2
    exit 1
fi
