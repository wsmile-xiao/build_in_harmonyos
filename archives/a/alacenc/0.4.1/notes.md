# alacenc 0.4.1 HarmonyOS PC notes

## Source

- Upstream: https://github.com/flacon/alacenc
- Version: v0.4.1
- Source archive: https://github.com/flacon/alacenc/archive/refs/tags/v0.4.1.tar.gz
- SHA256: `77cf92e38c972c01ae2c083c04f11778035ab1653c7111657a8d5fef2933d538`

The source archive was downloaded and hashed locally on 2026-08-05. It contains
the alacenc application, bundled ALAC codec sources, and bundled docopt.cpp.

## Build approach

- Use upstream CMake build.
- Disable shared-library mode and optional docopt tests/examples.
- Set `CMAKE_POLICY_VERSION_MINIMUM=3.5` so modern CMake accepts the bundled
  docopt.cpp `cmake_minimum_required(VERSION 3.1)` file.
- Install only the `alacenc` executable and package all relevant license files
  (MIT, Apache-2.0, APSL-2.0, and BSL-1.0 from bundled sources).
- Build with `-j1` for runner compatibility.

## Patches

- `0001-cmake-project-version.patch`: the v0.4.1 tag still declares CMake
  project version `0.4.0`; the patch aligns `alacenc --version` with package
  version `0.4.1`.
- `0002-use-cmake-endian-macro.patch`: OHOS does not provide the non-standard
  `BYTE_ORDER/LITTLE_ENDIAN/BIG_ENDIAN` macros expected by `types.h/types.cpp`.
  The patch uses upstream's own CMake-generated `TARGET_RT_LITTLE_ENDIAN` macro.

## Test inventory

- Upstream alacenc project: no first-party CTest/test target in the release tarball.
- Bundled docopt.cpp includes its own test files, but upstream alacenc CI only runs
  configure and build.
- Conan `test_package`: runs `alacenc --version`, `alacenc --help`, then uses
  `test_alacenc.py` to generate a PCM WAV file and verify the M4A header.

## Local build note

The Windows workspace uses the local Conan venv under
`H:\OpenHarmonyOsCompetition\.tools\conan-venv`, `CONAN_HOME` under
`H:\OpenHarmonyOsCompetition\.tools\conan-home`, and the MinGW profile at
`H:\OpenHarmonyOsCompetition\.tools\profiles\win-mingw` for native prechecks.

Local Windows/MinGW validation passed on 2026-08-05 after installing CMake into
the existing Conan venv and setting `TMP`, `TEMP`, and `TMPDIR` to
`H:\OpenHarmonyOsCompetition\.tools\tmp` to avoid sandbox-denied user temp paths.

- Command: `conan create archives/a/alacenc/0.4.1 -pr:h .tools/profiles/win-mingw -pr:b .tools/profiles/win-mingw -b missing`
- Exit code: `0`
- Full ref: `alacenc/0.4.1#4b9124ee39767d545ea243d9fe5ee959:77f6ce086c1b497b11d37729944960e5d3bd767d#f54c0f3e32a90e4f2295fc13cb79be7f`
- Consumer smoke: `alacenc --version`, `alacenc --help`, and generated WAV to
  M4A encode all passed.

## Runner notes

- The new-port profile sets `CONFIG_SHELL=/bin/sh`; `/data/service/hnp/bin/bash`
  is not present on this runner. The consumer smoke commands run directly through
  Conan's generated run environment.

## OHOS new-port verification

- Runner: `currentUser@frp-tip.com:33332`
- Job: `/storage/Users/currentUser/ohos-users/codex-a/alacenc-0.4.1-newport-r1`
- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-0.4.1-alacenc-0.4.1-newport-r1-conan-20260805-171316-20013`
- Started: `2026-08-05 17:13:16 +0800`
- Ended: `2026-08-05 17:13:46 +0800`
- Exit code: `0`
- Full ref: `alacenc/0.4.1#4b9124ee39767d545ea243d9fe5ee959:6b129b068851896169fae42d399fa922d239ce8a#3592a5d031f6d3d6084eb987e4f8270a`
- Results: L0 pass, L1 pass, L2 pass, L4 pass, L5 pass.
- Consumer smoke: `alacenc --version`, `alacenc --help`, and generated WAV to
  M4A encode all passed.
