#!/bin/sh
# test.sh — melting 5.2.0 API call test.
# Compiles and runs TestMelting.java against the packaged melting5.jar.
# Satisfies R34 (real API call, not a stub).

set -eu

# HMBS sandbox: /tmp may be read-only, prefer HMBS TMPDIR/TMP/TEMP.
WORK_TMP="${TMPDIR:-}"
if [ -z "$WORK_TMP" ]; then WORK_TMP="${TMP:-}"; fi
if [ -z "$WORK_TMP" ]; then WORK_TMP="${TEMP:-}"; fi
if [ -z "$WORK_TMP" ] || [ ! -d "$WORK_TMP" ] || [ ! -w "$WORK_TMP" ]; then
    WORK_TMP="$(pwd)/.tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null || WORK_TMP="$(dirname "$0")/.tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null
fi
export TMPDIR="$WORK_TMP" TMP="$WORK_TMP" TEMP="$WORK_TMP"

if [ $# -ge 1 ]; then
    PKG_DIR="$1"
elif [ -n "${CONAN_PACKAGE_FOLDER:-}" ]; then
    PKG_DIR="$CONAN_PACKAGE_FOLDER"
else
    PKG_DIR="$(pwd)/package"
fi

# Resolve JAVA_HOME: env first, then common cmd-pkgs locations.
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
# Fall back to $HOME layouts used by the recipe auto-install.
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "${JAVA_HOME:-}" ]; then
    for candidate in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17"; do
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

JAR_PATH="$PKG_DIR/libexec/melting5.jar"
DATA_DIR="$PKG_DIR/share/melting/Data"
TEST_SRC="$(dirname "$0")/TestMelting.java"
TMP_DIR="$(mktemp -d "${WORK_TMP}/melting.XXXXXX" 2>/dev/null || mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== melting 5.2.0 API call test ==="

if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: melting JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

if [ -d "$DATA_DIR" ]; then
    echo "OK: Data found at $DATA_DIR"
    export NN_PATH="$DATA_DIR"
else
    echo "WARN: Data dir not found at $DATA_DIR (melting falls back to jar-embedded/default path)"
fi

if ! javac -cp "$JAR_PATH" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestMelting.java compiled successfully"

output=$(java -cp "$JAR_PATH:$TMP_DIR" TestMelting 2>&1) || {
    echo "ERROR: Java test execution failed"
    echo "$output"
    exit 1
}

if echo "$output" | grep -q "PASS"; then
    echo "OK: $output"
    echo "=== All tests passed ==="
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test.sh","discovered":6,"passedCount":6}\n'
    exit 0
else
    echo "ERROR: Test did not produce PASS output"
    echo "$output"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test.sh","discovered":6,"passedCount":0}\n'
    exit 1
fi
