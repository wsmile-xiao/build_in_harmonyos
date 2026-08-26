# pico-sdk 2.2.0 HarmonyOS Adaptation Notes

## Scope

This adaptation packages Raspberry Pi `pico-sdk` 2.2.0 as an OHOS-native Conan package that provides:

- the host-side `pioasm` executable built from `tools/pioasm`;
- the SDK source/build files under `share/pico-sdk`;
- build/run environment variables for `PICO_SDK_PATH` and `PATH`.

The recipe intentionally does not attempt a full RP2040/RP2350 firmware build. Upstream firmware targets require a bare-metal ARM/RISC-V toolchain and are outside the OHOS-native package build.

## W0 Dependency Check

Conan dependencies: none.

Build tools expected from the build environment: CMake and a C++ compiler.

Optional/external SDK submodules in upstream `.gitmodules`:

- `lib/tinyusb` -> `https://github.com/hathach/tinyusb.git`
- `lib/cyw43-driver` -> `https://github.com/georgerobotics/cyw43-driver.git`
- `lib/lwip` -> `https://github.com/lwip-tcpip/lwip.git`
- `lib/mbedtls` -> `https://github.com/Mbed-TLS/mbedtls.git`
- `lib/btstack` -> `https://github.com/bluekitchen/btstack.git`

The Debian orig tarball used by this recipe keeps these submodule directories empty. This is acceptable for the current `pioasm` + SDK source package, but full USB/Wi-Fi/network/Bluetooth SDK consumers will need those dependencies handled separately rather than mixed into this PR.

## Source

Primary source used for Conan:

- URL: `https://deb.debian.org/debian/pool/main/p/pico-sdk/pico-sdk_2.2.0.orig.tar.gz`
- SHA256: `dbd8db79015aced4ef35cbaa88051b0d451775010d20202e1c7d2bee69c25b35`
- Debian source metadata checked: `pico-sdk_2.2.0-3.dsc`

GitHub release source archive was attempted first but timed out from this Windows environment. Debian's source package metadata confirms the same upstream version and checksum for the orig tarball.

## Build System Analysis

Top-level build system: CMake.

Relevant files:

- `CMakeLists.txt`
- `pico_sdk_init.cmake`
- `pico_sdk_version.cmake`
- `tools/pioasm/CMakeLists.txt`
- `src/CMakeLists.txt`

The top-level SDK CMake project initializes RP-series platform logic and tests. The Conan recipe configures only `tools/pioasm`, which is a standalone host tool with pre-generated lexer/parser sources. `PIOASM_GENERATE_PARSER` is disabled, so Bison/Flex are not required.

## Testing

Upstream `test/` contains CMake-based firmware-oriented test projects:

- `cmsis_test`
- `hardware_irq_test`
- `hardware_pwm_test`
- `hardware_sync_spin_lock_test`
- `kitchen_sink`
- `pico_divider_test`
- `pico_float_test`
- `pico_sem_test`
- `pico_sha256_test`
- `pico_stdio_test`
- `pico_stdlib_test`
- `pico_test`
- `pico_time_test`

These are not executed in the OHOS-native Conan build because they require RP-series target toolchains/platforms.

The recipe performs a build-time `pioasm` smoke by:

1. running `pioasm --version`;
2. assembling a minimal `.pio` program to a C SDK header;
3. checking the generated header contains `conan_smoke_program`.

The `pioasm` build passes `-j1` to the CMake backend to avoid OHOS/HMDFS jobserver FIFO issues seen in other packages.

The `test_package` repeats the consumer-side smoke and verifies:

1. `PICO_SDK_PATH` is exported;
2. `pico_sdk_version.cmake` exists in the package;
3. the version file reports 2.2.0;
4. `pioasm --version` runs;
5. `pioasm` generates a header containing the expected program symbols.

## Local Validation

Completed locally:

- downloaded Debian `pico-sdk_2.2.0.orig.tar.gz`;
- verified SHA256 `dbd8db79015aced4ef35cbaa88051b0d451775010d20202e1c7d2bee69c25b35`;
- expanded source and confirmed CMake + standalone `tools/pioasm`;
- confirmed upstream submodule directories are empty in the source tarball;
- `conan inspect` passed and reported `requires: []`;
- `conan source .` passed in a clean temporary recipe directory;
- `conan export` passed, recipe revision `14673ab33e88d6e6825bacf5175c8a70`;
- `conan graph info` passed with `ci/conan/profiles/ohos-aarch64`, dependency graph empty;
- Windows host `conan create` passed using a temporary Zig/Ninja/CMake profile, including `pioasm --version` and `.pio` to `.h` smoke checks in both build and `test_package`.

OHOS shadow CI completed:

- true-device shadow CI r4 passed on 2026-08-25;
- source commit: `0ad30b6f0da65d87c1afab9cf4e36de701df03d3`;
- runner dir: `/storage/Users/currentUser/ohos-test-runs/codex-pico-sdk-pico-sdk-2.2.0-shadow-ci-r4-20260825-215357-51430`;
- shadow dir: `/storage/Users/currentUser/ohos-users/codex/pico-sdk-2.2.0-ceaa7e184d/ohpc-ci-shadow/runs/20260825T135359Z-872357c2e6-51496`;
- results: `G0_RESULT=pass`, `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`, `L4_RESULT=pass`, `L5_RESULT=pass`, Build Summary `Total: 1 / Success: 1 / Failed: 0`.

Known CI environment notes:

- CI pre-download warned because `curl` was unavailable on the device, then Conan downloaded the Debian source URL successfully;
- `/data/service/hnp/bin/bash -lc` printed `/etc/profile: Permission denied`, but the pioasm commands returned success;
- `test_package` passes the absolute packaged `bin/pioasm` path to `smoke.py` so it does not depend on shell PATH resolution;
- official AtomGit CI build `#31318` failed before pico-sdk sources were compiled because the active OHOS SDK `lld` could not load `libxml2.so.16` (`xmlFreeDoc` and related symbols missing) during CMake's compiler probe;
- the recipe now derives the active SDK `llvm/lib` directory from `tools.build:compiler_executables` / `clang++ -print-resource-dir`, verifies `lld -flavor gnu --version` with that path prepended, and scopes `LD_LIBRARY_PATH` only to CMake configure/build.

## Next Verification Commands

Run on the OHOS/shadow CI environment as a single package:

```sh
CI_PACKAGES="archives/p/pico-sdk/2.2.0" zsh ci/conan/build_and_test.sh
```

Alternative runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/p/pico-sdk/2.2.0
```

Expected evidence to collect:

- CI only discovers `archives/p/pico-sdk/2.2.0`;
- `Build Summary` total is 1;
- L0/L1 pass;
- logs show `pioasm --version` and `.pio` to `.h` generation;
- L5 shows `bin/pioasm` and `share/pico-sdk/pico_sdk_version.cmake` exist.
