#!/usr/bin/env bash
# Bash wrapper around the Python consumer driver (OHOS CI runner requirement).
set -euo pipefail

: "${TEST_PYTHON:?TEST_PYTHON is not set}"
: "${TEST_SCRIPT:?TEST_SCRIPT is not set}"
: "${MBROLA_BIN:?MBROLA_BIN is not set}"
: "${MBROLA_GR2_ROOT:?MBROLA_GR2_ROOT is not set}"
: "${TEST_WORKDIR:?TEST_WORKDIR is not set}"

exec "$TEST_PYTHON" "$TEST_SCRIPT" "$MBROLA_BIN" "$MBROLA_GR2_ROOT" "$TEST_WORKDIR"
