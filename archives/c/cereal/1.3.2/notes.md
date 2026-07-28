# cereal 1.3.2 adaptation notes

## Scope

- Branch: feat/cereal-1.3.2
- Issue: #1557.
- Package path: archives/c/cereal/1.3.2

## W0 dependency check

- Required dependencies: none. cereal is a C++11 header-only library.
- Optional dependency: pthread is only exposed when the Conan option `thread_safe=True` is enabled on Linux/OHOS/FreeBSD.
- `conan list "cereal/1.3.2" -r=ohpcd`: recipe not found, so this package still needs publishing.
- `conan download "cereal/1.3.2" -r=ohpcd --only-recipe`: blocked by remote acceleration policy; the package absence was confirmed with `conan list`.

## Source and build-system analysis

- Upstream: https://github.com/USCiLab/cereal
- Version source: https://github.com/USCiLab/cereal/archive/v1.3.2.tar.gz
- sha256: 16a7ad9b31ba5880dac55d62b5d6f243c3ebc8d46a3514149e56b5e7ea81f85f
- Build system: upstream provides CMake.
- Packaging strategy: copy `include/cereal` directly because cereal is header-only. This avoids requiring CMake during the package step; CMake remains in the consumer `test_package` to verify `cereal::cereal` through Conan CMakeDeps.
- Upstream tests: cereal has a CTest/unittests tree, but it is not enabled in the package build for the header-only copy path. The consumer `test_package` performs a real API test by serializing and deserializing a struct with `BinaryOutputArchive` and `BinaryInputArchive`.

## Local preflight

- Conan version: 2.29.1.
- Remote: `ohpcd` configured and enabled.
- Host source download from GitHub was unstable from Windows. The OHOS runner used the CI mirror fallback and downloaded the source successfully.

## OHOS runner validation

- Machine: `currentUser@frp-tip.com:33332`
- Runner command: `ohos-test-runner.sh --user codex --lib cereal --task cereal-1.3.2-reviewfix --mode smoke --try-lock ...`
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-cereal-cereal-1.3.2-reviewfix-20260728-003342-62509`
- Result: pass, exit code 0.
- Build summary: Total 1, Success 1, Failed 0.
- Gate results:
  - L0: pass
  - L1: pass
  - L2: skip, no bin directory for header-only package
  - L4: pass
  - L5: warn, no bin/lib artifacts for header-only package
- Negative test: passed; CI moved `include/` away and confirmed the consumer test genuinely depends on cereal.

## Next validation commands

```sh
CI_PACKAGES="archives/c/cereal/1.3.2" zsh ci/conan/build_and_test.sh
```

Shadow CI single package:

```sh
/path/to/run-ohos-shadow-ci.sh archives/c/cereal/1.3.2
```

Direct Conan smoke command on OHOS runner:

```sh
cd archives/c/cereal/1.3.2
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```
