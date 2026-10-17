# Cubature 1.0.4 HarmonyOS PC adaptation notes

## Scope

- Official upstream tag: `v1.0.4`
- Upstream commit: `03d4af5f3ec30d2400e129bdb17739808c92dfd9`
- Build system: CMake
- Output: `libcubature.so` and `cubature.h`
- Dependencies: libc and the system math library only
- Source patches: none

## Adaptation

The implementation is portable C and compiles with HarmonyOS Clang without a
source change. CMake 4.x no longer accepts the upstream project's CMake 3.0
policy baseline by default, so the Conan toolchain supplies
`CMAKE_POLICY_VERSION_MINIMUM=3.5`. The installed library directory is fixed to
`lib` for the package layout.

The package declares `m` as a system library because the cubature
implementation uses standard mathematical functions. HarmonyOS ELF outputs are
self-signed before execution and packaging.

## Validation

The upstream `test.c` driver is built twice by upstream CMake:

- `htest`: h-adaptive algorithm, integrands 0 through 8
- `ptest`: p-adaptive algorithm, integrands 0 through 8

All 18 algorithm/integrand combinations are executed without changing the
upstream test source. The installed-package consumer separately validates
`hcubature`, `pcubature`, `hcubature_v`, and `pcubature_v`, including numerical
results, reported error bounds, and callback failure propagation.

An additional HarmonyOS-only test requires the compiler-provided `__OHOS__`
target macro, loads the signed `libcubature.so` with `dlopen`, verifies all five
public entry points with `dlsym`, and performs a real h-adaptive integral. This
test is enabled only when Conan targets `os=OHOS`.

Validation commands:

```bash
python3 scripts/ohc-run.py conan-verify cubature 1.0.4
zsh ci/conan/build_and_test.sh archives/c/cubature/1.0.4
```

Result: all build, upstream, consumer, package, security, and repository gates
pass for the HarmonyOS/OHOS 6.0 aarch64 target.
