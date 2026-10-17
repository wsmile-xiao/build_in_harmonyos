#!/bin/sh
# test_package/test_carla.sh — Carla 2.5.10 L1 smoke test.
#
# Carla is an audio plugin host (CLI tool). This test verifies:
#   1. carla-discovery-native binary exists in lib/carla/
#   2. carla-discovery-native runs and prints a usage line
#   3. libcarla_utils.so exists in lib/carla/
#
# Usage: test_carla.sh <package_folder>
set -eu

PKG_DIR="${1:?missing package_folder argument}"
CARLA_LIB="${PKG_DIR}/lib/carla"

# 1. carla-discovery-native must exist
DISCOVERY="${CARLA_LIB}/carla-discovery-native"
if [ ! -f "${DISCOVERY}" ]; then
    echo "FAIL: carla-discovery-native not found at ${DISCOVERY}" >&2
    exit 1
fi

# 2. carla-discovery-native with no args prints a usage line.
#    The binary has no --version flag; a live ELF that loaded its
#    shared libraries and reached main() prints "[carla] usage:".
OUT="$("${DISCOVERY}" 2>&1 || true)"
if ! echo "${OUT}" | grep -q "usage:"; then
    echo "FAIL: carla-discovery-native did not print usage: ${OUT}" >&2
    exit 1
fi

# 3. libcarla_utils.so must exist in lib/carla/
UTILS_LIB="${CARLA_LIB}/libcarla_utils.so"
if [ ! -f "${UTILS_LIB}" ]; then
    echo "FAIL: libcarla_utils.so not found at ${UTILS_LIB}" >&2
    exit 1
fi

echo "carla 2.5.10: discovery/utils verification OK"
