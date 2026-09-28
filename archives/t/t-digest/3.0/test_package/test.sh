#!/bin/sh
# test.sh — t-digest API call test.
# Compiles and runs TestTDigest.java against the packaged t-digest JAR.
# Satisfies R34 substantive verification (real quantile/cdf/merge calls).
# POSIX sh only: true machine has no bash (only /bin/sh).
set -eu

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -d "$candidate" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    echo "ERROR: JAVA_HOME not set and no JDK found in common locations." >&2
    echo "Set JAVA_HOME to a JDK 17+ installation path." >&2
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

JAR_PATH="$PKG_DIR/libexec/t-digest-3.0.jar"
TEST_SRC="$(dirname "$0")/TestTDigest.java"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== t-digest API call test ==="

if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: t-digest JAR not found at $JAR_PATH" >&2
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"javac TestTDigest.java && java TestTDigest\",\"discovered\":14,\"passedCount\":0}"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

if [ -n "${TDIGEST_JAR:-}" ] && [ "$TDIGEST_JAR" != "$JAR_PATH" ]; then
    echo "INFO: TDIGEST_JAR=$TDIGEST_JAR (using $JAR_PATH)" >&2
fi

if ! javac -cp "$JAR_PATH" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed" >&2
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"javac TestTDigest.java && java TestTDigest\",\"discovered\":14,\"passedCount\":0}"
    exit 1
fi
echo "OK: TestTDigest.java compiled successfully"

output=""
if ! output=$(java -cp "$JAR_PATH:$TMP_DIR" TestTDigest 2>&1); then
    echo "ERROR: Java test execution failed" >&2
    echo "$output" >&2
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"javac TestTDigest.java && java TestTDigest\",\"discovered\":14,\"passedCount\":0}"
    exit 1
fi
echo "$output"

if ! echo "$output" | grep -q "ALL TDIGEST CHECKS PASSED"; then
    echo "ERROR: Test did not report ALL TDIGEST CHECKS PASSED" >&2
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"javac TestTDigest.java && java TestTDigest\",\"discovered\":14,\"passedCount\":0}"
    exit 1
fi

passed_count=$(echo "$output" | grep "RESULT CHECKS" | sed 's/.*passed=\([0-9][0-9]*\).*/\1/')
case "$passed_count" in
    ''|*[!0-9]*)
        echo "ERROR: cannot parse passed count from test output" >&2
        printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"javac TestTDigest.java && java TestTDigest\",\"discovered\":14,\"passedCount\":0}"
        exit 1
        ;;
esac

printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"javac TestTDigest.java && java TestTDigest\",\"discovered\":14,\"passedCount\":$passed_count}"
echo "=== All tests passed ==="
exit 0
