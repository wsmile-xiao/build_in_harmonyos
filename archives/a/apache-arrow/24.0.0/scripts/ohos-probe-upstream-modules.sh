#!/usr/bin/env sh
# Probe heavy Apache Arrow upstream C++ test modules on HarmonyOS.
#
# The probe configures an isolated CMake build tree for one heavy module and
# tries to build a representative upstream test target.  It is intentionally a
# probe, not a claim that the full module test suite passed.

set -eu

usage() {
  printf '%s\n' \
    'Usage:' \
    '  sh scripts/ohos-probe-upstream-modules.sh --module MODULE --src SRC --toolchain FILE --build-dir DIR [options]' \
    '' \
    'Required:' \
    '  --module orc|flight   Heavy module to probe' \
    '  --src DIR             Arrow cpp/ source directory' \
    '  --toolchain FILE      Conan/CMake toolchain file' \
    '  --build-dir DIR       Probe build directory' \
    '' \
    'Options:' \
    '  --prefix DIR          Install prefix for the probe build' \
    '  --boost-src DIR       Existing Boost FetchContent source directory' \
    '  --gtest-src DIR       Existing GoogleTest FetchContent source directory' \
    '  --grpc-src DIR        Existing gRPC FetchContent source directory' \
    '  --cmake PATH          CMake executable (default: cmake)' \
    '  --target NAME         Representative target override' \
    '  --timeout SECONDS     Configure/build timeout (default: 1200)' \
    '' \
    'Examples:' \
    '  sh scripts/ohos-probe-upstream-modules.sh \' \
    '    --module orc \' \
    '    --src "$SRC" \' \
    '    --toolchain "$TOOLCHAIN" \' \
    '    --build-dir "$OHOS_JOB_BASE/build-upstream-tests-orc-probe-v1" \' \
    '    --boost-src "$BOOST_SRC" \' \
    '    --gtest-src "$GTEST_SRC"'
}

MODULE=
SRC=
TOOLCHAIN=
BUILD_DIR=
PREFIX=
BOOST_SRC=
GTEST_SRC=
GRPC_SRC=
CMAKE=${CMAKE:-cmake}
TARGET=
PROBE_TIMEOUT=${PROBE_TIMEOUT:-1200}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --module) MODULE=$2; shift 2 ;;
    --src) SRC=$2; shift 2 ;;
    --toolchain) TOOLCHAIN=$2; shift 2 ;;
    --build-dir) BUILD_DIR=$2; shift 2 ;;
    --prefix) PREFIX=$2; shift 2 ;;
    --boost-src) BOOST_SRC=$2; shift 2 ;;
    --gtest-src) GTEST_SRC=$2; shift 2 ;;
    --grpc-src) GRPC_SRC=$2; shift 2 ;;
    --cmake) CMAKE=$2; shift 2 ;;
    --target) TARGET=$2; shift 2 ;;
    --timeout) PROBE_TIMEOUT=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$MODULE" ] || [ -z "$SRC" ] || [ -z "$TOOLCHAIN" ] || [ -z "$BUILD_DIR" ]; then
  usage >&2
  exit 2
fi

PREFIX=${PREFIX:-"$BUILD_DIR/prefix"}

FETCH_ARGS=
[ -z "$BOOST_SRC" ] || FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_BOOST=$BOOST_SRC"
[ -z "$GTEST_SRC" ] || FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_GOOGLETEST=$GTEST_SRC"
[ -z "$GRPC_SRC" ] || FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_GRPC=$GRPC_SRC"

COMMON_ARGS="
  -DCMAKE_TOOLCHAIN_FILE=$TOOLCHAIN
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_SYSTEM_PROCESSOR=aarch64
  -DBOOST_CONTEXT_ARCHITECTURE=arm64
  -DBOOST_CONTEXT_ABI=aapcs
  -DCMAKE_INSTALL_PREFIX=$PREFIX
  -DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF
  -DCMAKE_FIND_USE_PACKAGE_REGISTRY=FALSE
  -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=FALSE
  -DARROW_DEPENDENCY_SOURCE=BUNDLED
  -DARROW_DEPENDENCY_USE_SHARED=ON
  -DARROW_BUILD_SHARED=ON
  -DARROW_BUILD_STATIC=OFF
  -DARROW_BUILD_TESTS=ON
  -DARROW_WITH_BACKTRACE=ON
  -DARROW_WITH_JAVA=OFF
  -DARROW_WITH_PYTHON=OFF
  -DARROW_USE_GLOG=OFF
  -DARROW_USE_LLD=OFF
  -DARROW_USE_SCCACHE=OFF
  $FETCH_ARGS
"

case "$MODULE" in
  orc)
    TARGET=${TARGET:-arrow-orc-adapter-test}
    MODULE_ARGS="
      -DARROW_ORC=ON
      -DARROW_COMPUTE=ON
      -DARROW_FILESYSTEM=ON
      -DARROW_IPC=ON
      -DARROW_CSV=OFF
      -DARROW_DATASET=OFF
      -DARROW_FLIGHT=OFF
      -DARROW_JSON=OFF
      -DARROW_PARQUET=OFF
      -DARROW_WITH_BROTLI=OFF
      -DARROW_WITH_BZ2=OFF
      -DARROW_WITH_LZ4=OFF
      -DARROW_WITH_RE2=OFF
      -DARROW_WITH_SNAPPY=OFF
      -DARROW_WITH_UTF8PROC=OFF
      -DARROW_WITH_ZSTD=OFF
    "
    ;;
  flight)
    TARGET=${TARGET:-arrow-flight-internals-test}
    MODULE_ARGS="
      -DARROW_FLIGHT=ON
      -DARROW_DEPENDENCY_USE_SHARED=OFF
      -DARROW_BUILD_SHARED=OFF
      -DARROW_BUILD_STATIC=ON
      -DARROW_COMPUTE=ON
      -DARROW_FILESYSTEM=ON
      -DARROW_IPC=ON
      -DARROW_CSV=OFF
      -DARROW_DATASET=OFF
      -DARROW_JSON=OFF
      -DARROW_ORC=OFF
      -DARROW_PARQUET=OFF
      -DARROW_WITH_BROTLI=OFF
      -DARROW_WITH_BZ2=OFF
      -DARROW_WITH_LZ4=OFF
      -DARROW_WITH_SNAPPY=OFF
      -DARROW_WITH_UTF8PROC=OFF
      -DARROW_WITH_ZSTD=OFF
    "
    ;;
  *)
    echo "Unsupported module: $MODULE" >&2
    exit 2
    ;;
esac

mkdir -p "$BUILD_DIR" "$PREFIX"

echo "RUN_DIR=${OHOS_TEST_RUN_DIR:-unknown}"
echo "MODULE=$MODULE"
echo "SRC=$SRC"
echo "BUILD_DIR=$BUILD_DIR"
echo "PREFIX=$PREFIX"
echo "TARGET=$TARGET"
echo "PROBE_TIMEOUT=$PROBE_TIMEOUT"

if [ ! -f "$BUILD_DIR/CMakeCache.txt" ]; then
  echo "== configure $MODULE =="
  # shellcheck disable=SC2086
  timeout "$PROBE_TIMEOUT" "$CMAKE" -S "$SRC" -B "$BUILD_DIR" -G "Unix Makefiles" \
    $COMMON_ARGS \
    $MODULE_ARGS
else
  echo "== configure skipped; cache exists =="
fi

echo "== dependency cache summary =="
grep -E '^(ARROW_(ORC|FLIGHT|WITH_(GRPC|PROTOBUF|ZLIB|RE2|UTF8PROC))|CMAKE_SYSTEM_PROCESSOR|BOOST_CONTEXT_)' \
  "$BUILD_DIR/CMakeCache.txt" 2>/dev/null || true

echo "== build representative target =="
if ! timeout "$PROBE_TIMEOUT" "$CMAKE" --build "$BUILD_DIR" --target "$TARGET" -- -j1; then
  echo "== target build failed; target help =="
  "$CMAKE" --build "$BUILD_DIR" --target help 2>/dev/null | grep -Ei 'orc|flight|grpc|protobuf' | head -120 || true
  exit 10
fi

echo "== probe target built =="
find "$BUILD_DIR" -maxdepth 5 -type f -name "$TARGET" -print 2>/dev/null || true
