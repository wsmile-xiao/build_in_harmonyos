# gflags 2.3.1 HarmonyOS PC adaptation

## Dependency boundary

gflags has no third-party Conan requirements. Its threaded target uses the platform C++ runtime and pthreads through upstream CMake `find_package(Threads)`.

## Source and version metadata

The recipe downloads upstream tag `v2.3.1` from the official GitHub codeload URL in `conandata.yml`, verifies SHA256 `1b5e0648d7b94021895086e65479b4eaca7935eecfffd7dd9512eb576181c53d` during `source()`, and unpacks the `.tar.gz` archive. The archive is fetched by Conan instead of being vendored in the repository. The tagged source still declares `PACKAGE_VERSION` as `2.3.0`, although the tag and release are `v2.3.1`. Patch `0002-cmake-version-match-tag.patch` corrects the generated CMake package metadata; the upstream 2.x ABI SONAME remains `2.3`.

## OHOS build

The recipe builds the shared library and a static copy for upstream tests, installs only the shared library, and disables the optional no-threads library. Patch `0001-use-static-gflags-for-ohos-tests.patch` links upstream test executables to the static copy on OHOS so CTest does not depend on target shared-library lookup during the build. Patch `0003-enable-shared-soname-on-ohos.patch` sets `NO_SONAME` to false and adds `-Wl,-soname,libgflags.so` to the shared target link on HarmonyOS because the platform CMake rules otherwise omit `DT_SONAME`.

The `conan-build/` directory avoids a case-insensitive Windows collision between upstream Bazel's `BUILD` file and Conan's default `build/` directory. The shell completion helper is removed from the package; the delivered artifact is a library and does not need `commands.json`.

## Verification

On HarmonyOS PC aarch64, `conan create` exited 0 and all 52 upstream CTest cases passed. The Conan consumer test passed 1/1 and printed `gflags answer=42`. The installed library reports `DT_SONAME` as `libgflags.so`, and `gflags-config-version.cmake` reports `PACKAGE_VERSION "2.3.1"`. The device does not provide `binary-sign-tool`, so the recipe preserves the linker-generated `.codesign` section; the shared library loaded successfully in the consumer test.
