#!/usr/bin/env bash
# libflorist test_package -- build the Ada consumer that links the packaged
# libflorist and calls its POSIX.5 bindings.
#
# Signing and execution are done by conanfile.py: OHOS refuses to exec an
# unsigned ELF (E489/E517).
#
# Arguments passed by conanfile.py:
#   $1 = floristlib dir of the package under test (Ada specs + libflorist.a)
#   $2 = GNAT runtime adainclude dir (from the gcc-ada tool_require)
#   $3 = GNAT runtime adalib dir
#   $4 = output executable path
#   $5 = work dir for compiler intermediates (object/ALI files)
#
# $5 matters: gnatmake writes .o/.ali next to the compiled unit, so compiling
# straight from this directory would litter the recipe tree with build
# artifacts.  All intermediates therefore go to the Conan build folder.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
FLORIST_DIR="${1:?floristlib dir required}"
ADA_INCLUDE="${2:-}"
ADA_OBJECTS="${3:-}"
OUTPUT="${4:?output path required}"
WORK_DIR="${5:-${SRC_DIR}/build-release}"

# PREPEND the GNAT runtime dirs so the paths contributed by the gcc-ada
# tool_require are preserved.  Without ADA_INCLUDE_PATH/ADA_OBJECTS_PATH
# gnatmake aborts with
#   fatal error, run-time library not installed correctly
if [ -n "${FLORIST_DIR}" ]; then
    ADA_INCLUDE_PATH="${FLORIST_DIR}${ADA_INCLUDE_PATH:+:$ADA_INCLUDE_PATH}"
    ADA_OBJECTS_PATH="${FLORIST_DIR}${ADA_OBJECTS_PATH:+:$ADA_OBJECTS_PATH}"
fi
if [ -n "${ADA_INCLUDE}" ]; then
    ADA_INCLUDE_PATH="${ADA_INCLUDE}${ADA_INCLUDE_PATH:+:$ADA_INCLUDE_PATH}"
fi
if [ -n "${ADA_OBJECTS}" ]; then
    ADA_OBJECTS_PATH="${ADA_OBJECTS}${ADA_OBJECTS_PATH:+:$ADA_OBJECTS_PATH}"
fi
export ADA_INCLUDE_PATH ADA_OBJECTS_PATH

echo "FLORIST_DIR=${FLORIST_DIR}"
echo "ADA_INCLUDE_PATH=${ADA_INCLUDE_PATH:-<unset>}"
echo "ADA_OBJECTS_PATH=${ADA_OBJECTS_PATH:-<unset>}"
echo "WORK_DIR=${WORK_DIR}"

mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

# -I<floristlib> resolves the library's Ada specs; -aL<floristlib> plus
# -lflorist resolves the static archive (libflorist.a) at link time.
# The consumer source is referenced by absolute path so that the object and
# ALI files stay in WORK_DIR instead of the recipe source tree.
rm -f "${OUTPUT}"
gnatmake -f -o "${OUTPUT}" "${SRC_DIR}/src/florist_consumer.adb" \
    -I"${SRC_DIR}/src" -I"${FLORIST_DIR}" \
    -aL"${FLORIST_DIR}" \
    -cargs -largs -lflorist

test -x "${OUTPUT}"
echo "built ${OUTPUT}"
