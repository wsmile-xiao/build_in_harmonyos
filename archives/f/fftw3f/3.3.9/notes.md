# fftw3f 3.3.9 adaptation notes

## Scope

- Target package: `fftw3f/3.3.9`
- Branch: `feat/fftw3f-3.3.9`
- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1451
- Dependency context: this package is adapted independently because `mvtools/29` is blocked on the unpublished `fftw3f/3.3.9` dependency.

## W0 Dependency Check

- Conan dependencies: none.
- System libraries: `m`; `pthread` only when the optional `threads` option is enabled.
- Remote recipe check: `conan download "fftw3f/3.3.9" -r=ohpcd --only-recipe` could not confirm publication on this machine because the remote returned `error:system acceleration policy not enabled`.

## Source And Build System

- Source URL: `https://www.fftw.org/fftw-3.3.9.tar.gz`
- SHA256: `bf2c7ce40b04ae811af714deb512510cc2c17b9ab9d6ddcf49fe4487eea7af3d`
- Upstream build systems: Autotools and CMake.
- Selected build system: CMake.

The existing `archives/f/fftw/3.3.10` notes say the Autotools path hit `config.guess`/`config.sub` OHOS recognition problems and was completed through CMake. This recipe follows that prior local evidence and sets `CMAKE_POLICY_VERSION_MINIMUM=3.5` for CMake 4 compatibility.

## Recipe Decisions

- Enable `ENABLE_FLOAT=ON` so upstream builds `libfftw3f`.
- Disable `BUILD_TESTS` in the package build to avoid target executable execution during cross-build.
- Disable OpenMP and SIMD options in the baseline recipe for a portable OHOS/aarch64 package.
- Keep `threads=False` by default; enabling it uses `ENABLE_THREADS=ON` and `WITH_COMBINED_THREADS=ON`.
- `test_package` builds and runs a consumer program that creates an `fftwf_plan_dft_1d`, executes forward and backward transforms, and checks the scaled round-trip values.

## Next Verification

Local precheck:

```sh
conan inspect .
conan export . --user=ohpcd --channel=stable
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

Single-package CI after a real device or shadow CI window is available:

```sh
CI_PACKAGES="archives/f/fftw3f/3.3.9" zsh ci/conan/build_and_test.sh
```

Shadow CI:

```sh
/path/to/run-ohos-shadow-ci.sh archives/f/fftw3f/3.3.9
```

## Local Precheck Results

Run on 2026-07-25 from `D:\harmonyos\worktrees\fftw3f`.

- `conan inspect .`: pass.
- `git diff --check -- archives/f/fftw3f/3.3.9`: pass.
- `python -m py_compile conanfile.py test_package/conanfile.py`: pass; generated `__pycache__` files were removed.
- `conan export . --user=ohpcd --channel=stable`: pass.
- `conan source .` in a temporary copy: pass; source downloaded and unpacked successfully.
- `conan create archives/f/fftw3f/3.3.9 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`: reached package build, then failed locally when the Windows shell tried to run the OHOS/Unix Makefiles CMake environment (`'.' is not recognized as an internal or external command`). This is a local host/profile mismatch; rerun on the OHOS build/shadow environment.
- Direct `cmake` configure precheck: not run; `cmake` is not installed in this Windows shell.

## Real Device Queue Results

Run on 2026-07-25 with issue 1451 on the shared OHOS device.

- `fftw3f-3.3.9-1451-conan-r2`: acquired the global device lock after 1806s, then failed before package build because the isolated Conan home had a stale `settings.yml` without `OHOS`.
- `fftw3f-3.3.9-1451-conan-r3`: seeded `settings.yml` from `$HOME/.conan2`, ran `ci/conan/setup.sh`, passed L0, exported the recipe, downloaded sources, then failed at CMake configure because `CMAKE_POLICY_VERSION_MINIMUM=3.5` was only set through the toolchain file and was not visible early enough for CMake 4's top-level policy check.
- `fftw3f-3.3.9-1451-conan-r4`: passed the CMake 4 policy check after passing `CMAKE_POLICY_VERSION_MINIMUM=3.5` through `cmake.configure()`, then failed because the copied CI profile points `tools.build:compiler_executables` to `/data/service/hnp/bin/clang`, which is not present on this shared device. The actual active shadow toolchain is under `$HOME/ohpc-ci-shadow/.../tools/clang`.
- `fftw3f-3.3.9-1451-conan-r5`: seeded `settings.yml`, patched only the isolated validation profile to use the active shadow clang wrappers, and passed with exit code 0. CI results: L0 pass, L1 pass, L2 skip (`no bin/ dir`), L4 pass (`no patches`), L5 pass. `test_package` printed `fftw3f test: OK (single-precision complex FFT round-trip succeeded)`.

## Upstream Test Results

Run on 2026-07-25 with issue 1451 on the shared OHOS device. No upstream test cases were modified.

- Upstream test entry point: Autotools `make check`, which runs `tests/check.pl` against the generated `tests/bench` executable.
- `fftw3f-3.3.9-1451-upstream-r6`: configured upstream Autotools with `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --enable-shared --enable-float --disable-fortran --disable-doc --disable-dependency-tracking`; the full `make -j1` build completed, then `make check -j1` failed because the device `make` parsed `-j1` as a missing-job-count option.
- `fftw3f-3.3.9-1451-upstream-r7`: reran the check phase as `make -j 1 check` against the r6 build directory. The check reached `tests/check.pl`, then failed with `perl: command not found` in the device validation environment.

Conclusion: upstream test execution is blocked by missing Perl runtime on the shared OHOS device, so no upstream pass rate is claimed. Package-level real-device Conan validation passed in r5, including the single-precision complex FFT round-trip `test_package`.
