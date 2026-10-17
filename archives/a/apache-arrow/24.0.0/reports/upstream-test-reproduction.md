# apache-arrow 24.0.0 upstream CTest reproduction notes

This note records the reproducible entry point used for the HarmonyOS upstream
CTest/GTest migration evidence.  The scripts are intentionally outside
`conanfile.py` because enabling `ARROW_BUILD_TESTS=ON` in the normal package
build expands Arrow's test dependency graph and may trigger network downloads.

## Scripts

- `scripts/ohos_arrow_relink_tests.py`
- `scripts/ohos-run-upstream-ctest.sh`
- `scripts/ohos-probe-upstream-modules.sh`
- `scripts/ohos_extract_tar_no_links.py`

The Python helper reads CMake `link.txt` files and relinks selected test
executables plus known Arrow/GTest helper shared libraries into one runtime
directory.  This avoids HarmonyOS loader issues caused by relative `NEEDED`
entries such as `../../release/libarrow_gtest.so`.

The shell wrapper then runs the relinked test executables with:

- single-directory `LD_LIBRARY_PATH`
- writable `TMPDIR` and `TEST_TMPDIR`
- optional `TZDIR`
- optional `ARROW_TEST_DATA`
- optional `PARQUET_TEST_DATA`

The heavy-module probe script configures a separate build tree for ORC or
Flight and attempts to build one representative upstream test target. Its
output is inventory/probe evidence only; it does not turn ORC or Flight on in
the regular Conan recipe.

`ohos_extract_tar_no_links.py` extracts a third-party source tarball while
copying symlink/hardlink entries as ordinary files or directories. It was added
for gRPC 1.46.3 because the current HarmonyOS test filesystem rejects link
creation, which makes CMake/libarchive extraction fail before any Flight target
can be configured.

The shell scripts intentionally avoid heredocs in their `--help` text. On the
current HarmonyOS device, `sh` may create heredoc temporary files under `/tmp`,
and `/tmp` can be read-only.

## Example

```sh
. "$HOME/ohos-users/codex/apache-arrow-isolated-base/env.sh"

sh "$CI_REPO_ROOT/archives/a/apache-arrow/24.0.0/scripts/ohos-run-upstream-ctest.sh" \
  --build-dir "$OHOS_JOB_BASE/build-upstream-tests-compute-temporal-v2" \
  --run-dir "$OHOS_JOB_BASE/build-upstream-tests-compute-temporal-v2/relinked-needed-run-repro" \
  --targets arrow-compute-vector-test,arrow-compute-aggregate-test \
  --tzdir "$HOME/.local/lib/python3.12/site-packages/tzdata/zoneinfo"
```

For Parquet tests, also pass:

```sh
--arrow-test-data "$OHOS_JOB_BASE/arrow-testing/data" \
--parquet-test-data "$OHOS_JOB_BASE/parquet-testing/data"
```

## Reproduction Boundary

The scripts reproduce selected C++ CTest/GTest executable targets from an
existing CMake build tree.  They do not claim to run the complete Apache Arrow
multi-language upstream suite.  Python, Java, R, CUDA, Gandiva and service-style
Flight tests require additional runtime, hardware or service setup and are
recorded separately in the inventory/difference reports.

## ORC / Flight Probe Entry

```sh
. "$HOME/ohos-users/codex/apache-arrow-isolated-base/env.sh"

SRC="$CONAN_HOME/p/b/apach51d0393c83636/b/cpp"
TOOLCHAIN="$CONAN_HOME/p/b/apach51d0393c83636/b/build-release/conan/conan_toolchain.cmake"
BOOST_SRC="$CONAN_HOME/p/b/apachae0288ac1ba8a/b/build-upstream-tests-p1-0003-arm64/_deps/boost-src"
GTEST_SRC="$CONAN_HOME/p/b/apachae0288ac1ba8a/b/build-upstream-tests-p1-0003-arm64/_deps/googletest-src"

sh "$CI_REPO_ROOT/archives/a/apache-arrow/24.0.0/scripts/ohos-probe-upstream-modules.sh" \
  --module orc \
  --src "$SRC" \
  --toolchain "$TOOLCHAIN" \
  --build-dir "$OHOS_JOB_BASE/build-upstream-tests-orc-probe-v1" \
  --boost-src "$BOOST_SRC" \
  --gtest-src "$GTEST_SRC"

sh "$CI_REPO_ROOT/archives/a/apache-arrow/24.0.0/scripts/ohos-probe-upstream-modules.sh" \
  --module flight \
  --src "$SRC" \
  --toolchain "$TOOLCHAIN" \
  --build-dir "$OHOS_JOB_BASE/build-upstream-tests-flight-probe-v1" \
  --boost-src "$BOOST_SRC" \
  --gtest-src "$GTEST_SRC" \
  --grpc-src "$OHOS_JOB_BASE/fetchcontent-src/grpc-1.46.3-no-links-v1/grpc-1.46.3"
```

To prepare the no-links gRPC source after the archive is available:

```sh
python3 "$CI_REPO_ROOT/archives/a/apache-arrow/24.0.0/scripts/ohos_extract_tar_no_links.py" \
  --archive "$OHOS_JOB_BASE/build-upstream-tests-flight-probe-v2/_deps/grpc-subbuild/grpc-populate-prefix/src/v1.46.3.tar.gz" \
  --dest "$OHOS_JOB_BASE/fetchcontent-src/grpc-1.46.3-no-links-v1"
```
