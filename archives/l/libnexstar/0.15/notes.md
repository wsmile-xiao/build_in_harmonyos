# libnexstar 0.15 HarmonyOS adaptation notes

## Source and dependency preflight

- Official source: `libnexstar-0.15.tar.gz` from the SourceForge project release.
- SHA-256: `7d4e14b47099fbe4362a4926e1b23d97546f9568c0d052582529a918910b7741`.
- Language preflight: C, compatible with the C/C++ task family.
- External Conan dependencies: none. Runtime interfaces are libc, libm, POSIX serial, and sockets.

## Build adaptation

The upstream project is Autotools-based. Its bundled GNU configuration files date from 2014 and reject the canonical `aarch64-linux-ohos` host. Minimal portability patches add HarmonyOS recognition to `config.guess` and `config.sub`. Two source-local headers used angle-bracket lookup and failed in a clean VPATH build; those includes now use quotes. The installed `libnexstar.pc` version is corrected from the stale upstream value 0.11 to 0.15.

The package defaults to a shared library because HarmonyOS has no system library with the same name. Setting `shared=False` produces the static variant. No generated file is carried as a patch. On OHOS, the recipe creates a dedicated `config-status-work` directory using the build tree's inherited permissions and rewrites only the extracted Autoconf `ac_tmp` assignment so generated helper files are written there. The upstream secure temporary-directory setup remains unchanged. This avoids HMDFS owner/mode mapping failures when writing `subs1.awk`.

## Upstream test inventory

The release has an empty `make check` target and no registered automated test framework. It ships seven manual/example C programs:

1. `testcode/celtest.c` — serial command transport and alignment reply.
2. `testcode/nexstarctl.c` — orientation, model, time, and version commands.
3. `testcode/nexstarctl2.c` — tracking-mode commands.
4. `examples/get_rade1.c` — precise coordinate retrieval.
5. `examples/get_rade2.c` — coordinate retrieval and display conversion.
6. `examples/push_buttons.c` — multi-axis fixed-rate slew sequence.
7. `examples/push_left.c` — single-axis fixed-rate slew sequence.

The adapted test package keeps `make check` in the build and automates these seven scenarios using full-duplex protocol simulation. Protocol/vendor enforcement uses each live socket endpoint and checks the public API result. Protocol command reads have a three-second `poll()` timeout so a regression cannot hang CI. An eighth OHOS-specific test is selected through CMake's `CMAKE_SYSTEM_NAME` (`HarmonyOS` or `OHOS`), verifies the AArch64/64-bit ABI contract, and calls the installed public conversion API without introducing a platform macro in source.

## Verification

- OHOS AArch64 shared-library configure/build/install: pass.
- Installed pkg-config version: 0.15.
- Upstream-derived automated scenarios: 7/7 pass.
- HarmonyOS-specific platform test: 1/1 pass.
- Total adapted tests: 8/8 pass (100%).

## PR #10079 repair

- CI builds #47907 and #48015 reproduced the same E167 failure: `config.status` could create a secure `conf*` directory on HMDFS, but could not write `subs1.awk` inside it. Build #48015 also proved that relocating `conf*` to Conan's `TMPDIR` was insufficient because that path is HMDFS-backed as well.
- The recipe now keeps the secure `conf*` setup intact and redirects only generated helper files to a recipe-created `config-status-work` directory with usable inherited permissions; it does not loosen permissions or modify shared CI infrastructure.
- `config.sub` now also contains an explicit `-linux-ohos*)` normalization guard before the generic `-linux*)` case, matching comparable legacy GNU configuration adaptations in this repository.
- CI builds #48023 and #48029 showed that `CMAKE_SYSTEM_PROCESSOR` is not a stable architecture contract for this native HarmonyOS CMake environment: even an explicit `-DCMAKE_SYSTEM_PROCESSOR=aarch64` did not survive with the expected value at the project assertion. The consumer recipe now validates the authoritative Conan `arch=armv8` setting, while `ohos_platform_test.c` independently requires the compiler's `__aarch64__` target macro and a 64-bit pointer ABI. The HarmonyOS-specific test remains mandatory and is never bypassed by the architecture check.
- Review findings were addressed by using valid socket descriptors for protocol enforcement, checking both enforcement API results, adding bounded protocol reads, and moving the OHOS selection into CMake.
---

**编译结束**: 2026-09-15 02:08
**最终状态**: built
