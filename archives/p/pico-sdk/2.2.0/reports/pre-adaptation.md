# pico-sdk 2.2.0 Pre-Adaptation Report

## Status

OHOS/shadow CI passed. Local source analysis, recipe/test_package authoring, Conan source/export/graph checks, Windows host conan create smoke, and true-device shadow CI are complete.

## W0

No Conan package dependencies are required for the chosen scope. The recipe builds the host-side `pioasm` tool from bundled generated C++ sources and packages SDK files.

External upstream submodules are not bundled in the source tarball:

- TinyUSB
- CYW43 driver
- LwIP
- MbedTLS
- BTstack

They are not needed for `pioasm` and are left out of this PR scope. If a downstream SDK feature requires them, adapt those dependency packages separately.

## Source Verification

Downloaded:

```text
https://deb.debian.org/debian/pool/main/p/pico-sdk/pico-sdk_2.2.0.orig.tar.gz
```

SHA256:

```text
dbd8db79015aced4ef35cbaa88051b0d451775010d20202e1c7d2bee69c25b35
```

Debian `.dsc` for `2.2.0-3` lists the same SHA256 and source size `2496942`.

## Build System

Detected systems:

- CMake: primary upstream build system;
- Bazel: metadata present but not used;
- `tools/pioasm`: standalone CMake subproject.

Recipe configuration:

- `build_script_folder=tools/pioasm`
- `PIOASM_VERSION_STRING=2.2.0`
- `PIOASM_GENERATE_PARSER=OFF`
- `cmake --build ... -- -j1`

## Test Strategy

Full upstream firmware tests are not run because they are target-device SDK tests for RP-series microcontrollers.

The build and test_package smoke exercises the packaged OHOS-native surface:

- execute `pioasm --version`;
- assemble `conan_smoke.pio`;
- verify the generated C SDK header contains expected program symbols;
- verify `PICO_SDK_PATH` points to packaged SDK files.

## Local Validation

Validated locally with the existing Conan 2.29.1 venv at `D:\harmonyos\worktrees\_codex-conan-client-2240` and temporary tools installed under workspace `work/`:

- `conan inspect` passed and reported no requirements;
- `conan source .` passed in a clean temporary recipe directory;
- `conan export` passed with recipe revision `14673ab33e88d6e6825bacf5175c8a70`;
- `conan graph info` passed with `ci/conan/profiles/ohos-aarch64` and an empty dependency graph;
- Windows host `conan create` passed with a temporary Zig/Ninja/CMake profile.

The Windows host `conan create` evidence included:

- built `bin/pioasm.exe` from `tools/pioasm`;
- build-time `pioasm --version` printed `pioasm version: 2.2.0`;
- build-time `.pio` to `.h` smoke generated `conan_smoke_program`;
- `test_package` verified `PICO_SDK_PATH` via `VirtualRunEnv`;
- `test_package` ran `pioasm --version` and generated `conandata_smoke.pio.h`.

OHOS-native shadow CI r4 passed on 2026-08-25 for source commit `0ad30b6f0da65d87c1afab9cf4e36de701df03d3`.

Evidence:

- runner dir: `/storage/Users/currentUser/ohos-test-runs/codex-pico-sdk-pico-sdk-2.2.0-shadow-ci-r4-20260825-215357-51430`;
- shadow dir: `/storage/Users/currentUser/ohos-users/codex/pico-sdk-2.2.0-ceaa7e184d/ohpc-ci-shadow/runs/20260825T135359Z-872357c2e6-51496`;
- `G0_RESULT=pass`;
- `L0_RESULT=pass: all checks passed`;
- `L1_RESULT=pass: test_package executed`;
- `L2_RESULT=pass: pioasm --version OK`;
- `L4_RESULT=pass: no patches`;
- `L5_RESULT=pass: bin/ has content`;
- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`.
Official AtomGit CI follow-up:

- build `#31318` on worker `OpenHarmonyPCDeveloper-CI-036` failed in CMake's compiler probe before pico-sdk source compilation;
- failure signature matched existing knowledge E120/E132/E266: OHOS SDK `lld` could not load `libxml2.so.16`, with `xmlFreeDoc` and related relocation symbols missing;
- fix: derive the active SDK `llvm/lib` directory from the configured compiler, probe `lld -flavor gnu --version` with that path in `LD_LIBRARY_PATH`, and apply the environment only around CMake configure/build.
