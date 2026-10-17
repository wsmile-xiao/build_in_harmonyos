#!/usr/bin/env bash
# Run the complete upstream test set and make legacy runners propagate failure.
set -euo pipefail

command -v node >/dev/null 2>&1 || {
    echo "uglifycss requires a Node.js runtime in PATH" >&2
    exit 1
}

node --jitless tests-yui.js
if find tests-yui -name '*.FAILED' -type f | grep -q .; then
    echo "UglifyCSS YUI regression failures:" >&2
    find tests-yui -name '*.FAILED' -type f -print >&2
    exit 1
fi

# tests-url.sh invokes the source CLI through its Node shebang. Execute the
# same three upstream scenarios with the JIT-disabled Node invocation required
# by the OpenHarmony runtime.
url_output=$(sed \
    -e 's#^\([[:space:]]*\)\./uglifycss #\1node --jitless ./uglifycss #' \
    -e 's#^\([[:space:]]*\)\.\./\.\./\.\./uglifycss #\1node --jitless ../../../uglifycss #' \
    -e 's#/tmp/uglifycss-tests-url\.tmp#${TMPDIR:-.}/uglifycss-tests-url.tmp#g' \
    tests-url.sh | sh)
printf '%s\n' "$url_output"
if printf '%s\n' "$url_output" | grep -q 'KO'; then
    echo "UglifyCSS URL conversion regression failure" >&2
    exit 1
fi
