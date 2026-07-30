# zimg 3.0.6 adaptation notes

## Scope

- Target library: zimg
- Version: 3.0.6
- Branch: feat/zimg-3.0.6
- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1459
- Downstream blocker: vapoursynth/74 requires zimg >= 3.0.5 and failed W0/Conan dependency resolution because zimg/3.0.6 was not available in remotes.

## W0 dependency check

zimg has no external Conan requirements.

Local command attempted:

```sh
conan download "zimg/3.0.6" -r=ohpcd --only-recipe
```

This environment returned `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`, so this workstation could not conclusively query the remote. The upstream vapoursynth/74 precheck already observed the package-not-resolved failure for zimg/3.0.6.

## Source verification

- Source URL: https://github.com/sekrit-twc/zimg/archive/refs/tags/release-3.0.6.tar.gz
- SHA256: be89390f13a5c9b2388ce0f44a5e89364a20c1c57ce46d382b1fcc3967057577
- Upstream build system: Autotools (`configure.ac`, `Makefile.am`, `autogen.sh`)
- Recipe build strategy: direct clang++ build of `src/zimg`
- License: WTFPL (`COPYING`)

The release archive does not contain generated `configure` files. `autogen.sh` runs `autoreconf --verbose --install --force`, but the OHOS CI image used for validation does not provide `autoreconf`. The recipe therefore compiles the zimg library sources directly with the Conan-provided compiler.

## Build choices

- No external dependencies are declared.
- The recipe builds `src/zimg/**/*.cpp` directly and includes only the target architecture backend (`ZIMG_ARM` on OHOS/aarch64).
- The default package is shared and self-signs `libzimg.so*` on OHOS before `test_package` execution.
- `zimg.pc` is generated during packaging with `Libs.private: -lc++` on OHOS.
- Upstream `make check` is not integrated in this recipe because it depends on the missing Autotools generation step and the gtest unit-test subtree is not shipped in the GitHub release archive.

## Consumer test

`test_package/test.cpp` links against `zimg::zimg` and calls real C API entry points:

- `zimg_get_version_info`
- `zimg_get_api_version`
- `zimg_image_format_default`
- `zimg_graph_builder_params_default`
- `zimg_filter_graph_build`
- `zimg_filter_graph_get_tmp_size`
- `zimg_filter_graph_free`

## Next validation commands

Local CI/shadow CI should be run as a single-package job when a HarmonyOS device window is available:

```sh
CI_PACKAGES="archives/z/zimg/3.0.6" zsh ci/conan/build_and_test.sh
```

If using the shadow CI wrapper:

```sh
/path/to/run-ohos-shadow-ci.sh archives/z/zimg/3.0.6
```

Expected checks before PR:

- Build summary shows Total: 1.
- L0/L1 pass.
- L2 may skip because zimg is a pure library with no installed command.
- L4 warnings, if any, are reviewed.
- L5 confirms `lib/libzimg.*`, `include/zimg.h`, `include/zimg++.hpp`, and `lib/pkgconfig/zimg.pc` are present.

## True-device validation

Device check on 2026-07-25 showed the global test lock free and no active
`conan`, `cmake`, `ninja`, `make`, or `clang` build processes, so a single
package zimg run was started.

Run directory:

```sh
/storage/Users/currentUser/ohos-test-runs/codex-zimg-3.0.6-zimg-3.0.6-20260725-213132-conan-20260725-220345-26058
```

Command:

```sh
zsh ci/conan/build_and_test.sh archives/z/zimg/3.0.6
```

Result:

- Exit code: 0
- L0_RESULT=pass: all checks passed
- L1_RESULT=pass: test_package executed
- L2_RESULT=skip: no bin/ dir
- L4_RESULT=pass: no patches
- L5_RESULT=pass: lib/ has content
- Build summary: Total 1, Success 1, Failed 0

The test package compiled and ran the consumer API smoke test:

```text
zimg 3.0.6 API 2.4 smoke test passed
```

Notes from device setup:

- Isolated `CONAN_HOME` initially needed `settings.yml` copied from the device
  default Conan home so that the OHOS setting exists.
- The recipe used the staged source archive at
  `/storage/Users/currentUser/Download/zimg-release-3.0.6.tar.gz` because direct
  GitHub download timed out on the device; the staged archive matched the
  recorded SHA256.
- The OHOS profile configured `/data/service/hnp/bin/clang++`, which was absent
  on this device. The recipe and test_package resolve the available
  `$HOME/usr/local/bin/clang++` wrapper and invoke script wrappers via `sh`.
