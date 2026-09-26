#!/bin/sh
# test_package/test.sh — smoke test for the installed orbuculum command line tools.
# Runs in the conanrun environment (PATH contains the package bin/ directory).
# POSIX sh only (the CI worker does not guarantee bash on PATH).
set -eu

fail() {
    echo "FAIL: $1"
    exit 1
}

TOOLS="orbuculum orbfifo orbcat orbtop orbdump orbstat orbmortem orbprofile orbtrace orbzmq orblcd"

installed=0
versioned=0
for tool in ${TOOLS}; do
    command -v "${tool}" >/dev/null 2>&1 || fail "${tool} is not installed in the package bin/"
    installed=$((installed + 1))
    # orbprofile is a development preview without a version switch.
    if [ "${tool}" = "orbprofile" ]; then
        continue
    fi
    output="$("${tool}" -V 2>&1 || true)"
    case "${output}" in
        *2.2.0*)
            echo "PASS: ${tool} -V reports 2.2.0"
            versioned=$((versioned + 1))
            ;;
        *)
            fail "${tool} -V did not report 2.2.0 (got: ${output})"
            ;;
    esac
done
echo "PASS: ${installed}/11 command line tools installed, ${versioned}/10 report version 2.2.0"
