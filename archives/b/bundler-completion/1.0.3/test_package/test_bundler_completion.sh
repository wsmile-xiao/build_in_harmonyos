#!/bin/bash
# test_package/test_bundler_completion.sh
# Consumer-side verification of the installed bundler bash completion.
set -euo pipefail

COMPLETION_FILE="${1:-}"

if [ -z "$COMPLETION_FILE" ]; then
    echo "Usage: $0 <installed completion file>"
    exit 1
fi

# 1. The completion file is installed at the documented path
if [ ! -f "$COMPLETION_FILE" ]; then
    echo "FAIL: completion file not found at $COMPLETION_FILE"
    exit 1
fi

# 2. It is valid bash source
bash -n "$COMPLETION_FILE"

# 3. The upstream completion entry point is defined
if ! grep -q '^__bundle()' "$COMPLETION_FILE"; then
    echo "FAIL: __bundle() is not defined"
    exit 1
fi

# 4. It registers the completion function for the bundle commands
if ! grep -q 'complete -F __bundle' "$COMPLETION_FILE"; then
    echo "FAIL: 'complete -F __bundle' registration not found"
    exit 1
fi

# 5. Sourcing it actually registers the completion with bash
if ! bash --noprofile --norc -c "source '$COMPLETION_FILE' && complete -p bundler" | grep -q -- '-F __bundle'; then
    echo "FAIL: sourcing the file did not register a completion for 'bundler'"
    exit 1
fi

# 6. The same registration is visible for the 'bundle' alias
if ! bash --noprofile --norc -c "source '$COMPLETION_FILE' && complete -p bundle" | grep -q -- '-F __bundle'; then
    echo "FAIL: sourcing the file did not register a completion for 'bundle'"
    exit 1
fi

echo "PASS: bundler-completion package verified ($COMPLETION_FILE)"
