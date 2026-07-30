#!/usr/bin/env sh
# Run selected Apache Arrow upstream GTest executables on HarmonyOS.
#
# This wrapper expects an existing Arrow CMake test build tree.  It relinks the
# selected CTest executable targets into one runtime directory and then runs the
# relinked binaries directly with a stable TMPDIR/TZDIR/LD_LIBRARY_PATH setup.

set -eu

usage() {
  printf '%s\n' \
    'Usage:' \
    '  sh scripts/ohos-run-upstream-ctest.sh --build-dir BUILD --targets TARGETS [options]' \
    '' \
    'Required:' \
    '  --build-dir DIR       Arrow CMake build directory' \
    '  --targets LIST        Comma-separated CTest executable targets' \
    '' \
    'Options:' \
    '  --run-dir DIR         Relinked runtime/log directory (default: BUILD/relinked-needed-run)' \
    '  --tmp-dir DIR         Temporary directory (default: RUN_DIR/tmp)' \
    '  --tzdir DIR           IANA zoneinfo directory for Arrow vendored date' \
    '  --arrow-test-data DIR ARROW_TEST_DATA directory' \
    '  --parquet-test-data DIR PARQUET_TEST_DATA directory' \
    '  --gtest-filter EXPR   GTest filter applied to every target' \
    '  --python PYTHON       Python executable (default: python3)' \
    '' \
    'Example:' \
    '  sh scripts/ohos-run-upstream-ctest.sh \' \
    '    --build-dir "$OHOS_JOB_BASE/build-upstream-tests-compute-temporal-v2" \' \
    '    --targets arrow-compute-vector-test,arrow-compute-aggregate-test \' \
    '    --tzdir "$HOME/.local/lib/python3.12/site-packages/tzdata/zoneinfo"'
}

BUILD_DIR=
RUN_DIR=
TMP_DIR=
TZDIR_VALUE=
ARROW_TEST_DATA_VALUE=
PARQUET_TEST_DATA_VALUE=
GTEST_FILTER=
PYTHON_BIN=${PYTHON_BIN:-python3}
TARGETS=

while [ "$#" -gt 0 ]; do
  case "$1" in
    --build-dir) BUILD_DIR=$2; shift 2 ;;
    --run-dir) RUN_DIR=$2; shift 2 ;;
    --tmp-dir) TMP_DIR=$2; shift 2 ;;
    --tzdir) TZDIR_VALUE=$2; shift 2 ;;
    --arrow-test-data) ARROW_TEST_DATA_VALUE=$2; shift 2 ;;
    --parquet-test-data) PARQUET_TEST_DATA_VALUE=$2; shift 2 ;;
    --gtest-filter) GTEST_FILTER=$2; shift 2 ;;
    --python) PYTHON_BIN=$2; shift 2 ;;
    --targets) TARGETS=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$BUILD_DIR" ] || [ -z "$TARGETS" ]; then
  usage >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_DIR=$(CDPATH= cd -- "$BUILD_DIR" && pwd)
RUN_DIR=${RUN_DIR:-"$BUILD_DIR/relinked-needed-run"}
TMP_DIR=${TMP_DIR:-"$RUN_DIR/tmp"}

mkdir -p "$RUN_DIR" "$TMP_DIR"

RELINK_ARGS=
OLD_IFS=$IFS
IFS=,
for target in $TARGETS; do
  [ -n "$target" ] || continue
  RELINK_ARGS="$RELINK_ARGS --target $target"
done
IFS=$OLD_IFS

# shellcheck disable=SC2086
"$PYTHON_BIN" "$SCRIPT_DIR/ohos_arrow_relink_tests.py" \
  --build-dir "$BUILD_DIR" \
  --run-dir "$RUN_DIR" \
  $RELINK_ARGS

export LD_LIBRARY_PATH="$RUN_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR="$TMP_DIR"
export TEST_TMPDIR="$TMP_DIR"
[ -z "$TZDIR_VALUE" ] || export TZDIR="$TZDIR_VALUE"
[ -z "$ARROW_TEST_DATA_VALUE" ] || export ARROW_TEST_DATA="$ARROW_TEST_DATA_VALUE"
[ -z "$PARQUET_TEST_DATA_VALUE" ] || export PARQUET_TEST_DATA="$PARQUET_TEST_DATA_VALUE"

echo "RUN_DIR=$RUN_DIR"
echo "BUILD_DIR=$BUILD_DIR"
echo "TARGETS=$TARGETS"
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "TMPDIR=$TMPDIR"
[ -z "${TZDIR:-}" ] || echo "TZDIR=$TZDIR"
[ -z "${ARROW_TEST_DATA:-}" ] || echo "ARROW_TEST_DATA=$ARROW_TEST_DATA"
[ -z "${PARQUET_TEST_DATA:-}" ] || echo "PARQUET_TEST_DATA=$PARQUET_TEST_DATA"

status=0
IFS=,
for target in $TARGETS; do
  [ -n "$target" ] || continue
  echo "===== $target ====="
  if [ -n "$GTEST_FILTER" ]; then
    "$RUN_DIR/$target" "--gtest_filter=$GTEST_FILTER" || status=$?
  else
    "$RUN_DIR/$target" || status=$?
  fi
done
IFS=$OLD_IFS

exit "$status"
