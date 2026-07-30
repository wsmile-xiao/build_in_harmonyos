# libchardet 1.0.6 HarmonyOS adaptation notes

## Scope

- Requested package: `libchardet/1.0.6`.
- Upstream match found for this version: `Joungkyun/libchardet` tag `1.0.6`.
- Archive path and branch follow the requested name `libchardet`.
- Issue: `#1561`.
- Branch: `feat/libchardet-1.0.6`.
- Worktree: `D:\harmonyos\worktrees\libchardet`.

## W0 dependency check

- Runtime/link dependencies: none found in upstream source.
- Build tools detected from `configure.ac` before patching:
  - C compiler
  - C++ compiler
  - libtool/autotools make flow
  - `date`
- Upstream also had a hard `AC_PATH_PROG(PERL, perl)` check, but that value is not used by the configured build/test path for this release.
- User clarified that Perl is not merged on main yet and Perl-related checks may be exempted.
- Recipe therefore does not declare `perl/5.42.2`; `patches/0001-fix-ohos-autotools-tests.patch` removes the unused Perl probe from `configure.ac` and neutralizes the same generated fatal check in the shipped `configure`.

## Source and build-system analysis

- Source URL: `https://github.com/Joungkyun/libchardet/archive/refs/tags/1.0.6.tar.gz`
- SHA256: `425f3fa9e7afa0ebc3f4e3572637fb87bd6541e2716ad2c18f175995eb2021f0`
- Build system: Autotools (`configure.ac`, generated `configure`, `Makefile.am/in`).
- Installed library name: `libchardet`.
- Public header install path: `include/chardet`.
- Public API header: `chardet.h`.
- Version 1.0.6 adds `DetectObj::bom` and `CHARDET_BOM_CHECK`.

## Recipe strategy

- Conan package name follows the requested target: `libchardet`.
- Upstream project/library metadata is recorded as `libchardet`.
- Use `AutotoolsToolchain` and `Autotools`.
- Default to static library with `--enable-static --disable-shared` to avoid first-pass OHOS shared-library signing and runtime loader issues.
- Keep upstream `make check` in `build()`; official tests are `bom-test`, `sample`, and `sample1`.
- Use a scoped patch file for the `configure.ac` and generated `configure` Perl cleanup so this package is not blocked on the separate Perl PR.
- Derive `llvm-ar`, `llvm-ranlib`, `llvm-strip`, `llvm-nm`, and `ld.lld` from the configured clang path and inject them into the Autotools build environment. The OHOS runner's non-interactive PATH may not expose bare binutils.
- Pass `--build=aarch64-unknown-linux-gnu` on OHOS because upstream `tools/config.guess` from 2017 cannot identify `uname -s = HarmonyOS`.
- On OHOS, replace the generated `configure` shebang with `/system/bin/sh` and relax `umask 077` to `umask 002`, following the existing fribidi-style OHOS Autotools workaround.
- Add the source `include` directory to C/C++ flags for out-of-source Autotools builds; upstream source files include headers such as `nscore.h` from that directory.
- Patch test `Makefile.am/in` so `make check` links against the out-of-source build directory `libchardet.la`, and uses the C++ linker for C smoke binaries that link the static C++ library.
- Remove libtool `.la` files and the `chardet-config` script from the package; Conan metadata and `chardet.pc` remain the supported consumption paths.

## Test package

`test_package` uses CMakeDeps/CMakeToolchain and compiles a real consumer:

- includes `<chardet.h>`;
- calls `detect_version()`;
- verifies `CHARDET_BINARY_SAFE`;
- verifies `CHARDET_BOM_CHECK`;
- calls `detect_r()` on UTF-8 BOM text and expects `UTF-8` plus `bom == 1`;
- calls `detect_r()` on ASCII text and expects `ASCII` plus `bom == 0`.

## Local validation performed

- Main worktree was not switched; libchardet work happened in `D:\harmonyos\worktrees\libchardet`.
- Created branch `feat/libchardet-1.0.6` from current `origin/main`.
- Downloaded upstream source tarball and calculated SHA256.
- Inspected upstream Autotools files, public header, official tests, and README.
- Confirmed local Conan version: `2.29.1`.
- Local host lacks `cmake`; full `conan create` is not suitable on this Windows host.

## OHOS validation status

- Runner: `ssh -T -p 33332 -i "$env:USERPROFILE\.ssh\ohos_pc_codex_ed25519" currentUser@frp-tip.com`
- Isolated job base: `/storage/Users/currentUser/ohos-users/codex-libchardet/libchardet-1.0.6`
- Final RUN_ID: `codex-libchardet-1.0.6-libchardet-1.0.6-reviewfix-conan-20260729-103147-50726`
- Command shape: `CI_PACKAGES="archives/l/libchardet/1.0.6" zsh ci/conan/build_and_test.sh`
- Result: passed on OHOS runner.
- Upstream `make check`: `bom-test`, `sample`, and `sample1` all PASS (`3/3`, `100%`).
- `test_package`: CMake consumer builds and executes `test_libchardet`; output: `libchardet 1.0.6 smoke OK`.
- CI gates: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip: no bin/ dir`, `L4_RESULT=pass`, `L5_RESULT=pass`.
- Runner note: the first corrected run was blocked by a stale lock and corrupted isolated Conan `global.conf`/`remotes.json` from the earlier interrupted SSH session; rerun used a clean isolated `CONAN_HOME` copied from the runner's normal Conan config.

## Next commands

Re-run true-device or shadow CI, single package only:

```sh
CI_PACKAGES="archives/l/libchardet/1.0.6" zsh ci/conan/build_and_test.sh
```

Shadow CI runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/l/libchardet/1.0.6
```

Perl-related W0/CI checks are intentionally exempt for this package until Perl lands on main.
