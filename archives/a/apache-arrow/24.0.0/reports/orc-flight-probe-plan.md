# apache-arrow 24.0.0 ORC / Flight probe plan

## Purpose

This plan records the next heavy probes for modules that are not enabled in the
regular apache-arrow recipe.  The probes are Path B boundary evidence, not
package guarantees.

If a third-party source archive contains symlink or hardlink entries and the
current device filesystem rejects link creation, pre-extract it with
`scripts/ohos_extract_tar_no_links.py` and pass the resulting source directory
to the probe.

## ORC Probe

Representative target:

- `arrow-orc-adapter-test`

Expected dependency expansion:

- ORC
- protobuf
- zlib

Command skeleton:

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
```

## Flight Probe

Representative target:

- `arrow-flight-internals-test`

Expected dependency expansion:

- gRPC
- protobuf
- re2
- zlib
- OpenSSL / BoringSSL
- service-style test runtime

Command skeleton:

```sh
. "$HOME/ohos-users/codex/apache-arrow-isolated-base/env.sh"

SRC="$CONAN_HOME/p/b/apach51d0393c83636/b/cpp"
TOOLCHAIN="$CONAN_HOME/p/b/apach51d0393c83636/b/build-release/conan/conan_toolchain.cmake"
BOOST_SRC="$CONAN_HOME/p/b/apachae0288ac1ba8a/b/build-upstream-tests-p1-0003-arm64/_deps/boost-src"
GTEST_SRC="$CONAN_HOME/p/b/apachae0288ac1ba8a/b/build-upstream-tests-p1-0003-arm64/_deps/googletest-src"

sh "$CI_REPO_ROOT/archives/a/apache-arrow/24.0.0/scripts/ohos-probe-upstream-modules.sh" \
  --module flight \
  --src "$SRC" \
  --toolchain "$TOOLCHAIN" \
  --build-dir "$OHOS_JOB_BASE/build-upstream-tests-flight-probe-v1" \
  --boost-src "$BOOST_SRC" \
  --gtest-src "$GTEST_SRC" \
  --grpc-src "$OHOS_JOB_BASE/fetchcontent-src/grpc-1.46.3-no-links-v1/grpc-1.46.3"
```

Observed probe results:

- v2 RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v2-20260727-040342-62286`
- v2 result: gRPC download completed, but source extraction failed on link entries because the device filesystem rejects symlink/hardlink creation.
- v3 RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v3-20260727-042031-3517`
- v3 result: pre-extracted gRPC source passed extraction, then Flight tests required static Arrow linkage.
- v4 RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v4-20260727-043233-9482`
- v4 result: static Arrow + pre-extracted gRPC configured, then CMake generate failed due to missing `OpenSSL::SSL` / `OpenSSL::Crypto`.

## Device Note

Run these only through the shared HarmonyOS runner when the heavy lock is free.
If dependency downloads or configure fail, keep the log as environment/dependency
evidence rather than marking the upstream target itself as failed.
