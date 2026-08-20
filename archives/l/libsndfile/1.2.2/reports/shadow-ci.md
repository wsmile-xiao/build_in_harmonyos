# HarmonyOS aarch64 shadow CI report

## Result

- Issue: AtomGit #31
- Package: `archives/l/libsndfile/1.2.2`
- Tested commit: `f2707f8869c6d560d848bce0686c705180ac9894`
- Runner: `local-ohos-shadow-device1`
- Device kernel: HongMeng Kernel 1.12.0, aarch64
- Toolchain: clang 15.0.4, Python 3.12.9, Conan 2.29.1
- Completed: 2026-08-17 03:48:23 UTC
- Final status: pass

The run was serialized through both the device-global lock and the shadow
runner lock. Both locks were released after completion.

## Input verification

- Source archive SHA-256: `0b89c777889272b5aad2cf1c9250ab3a74b9d4b0d2991f7b053cd5ec0b1c7643`
- `ci/conan/setup.sh`: `d93c97005abe8e5c3cc8bd1076815b3a34654a523fc8c4dc8a2415a68e8367b7`
- `ci/conan/build_and_test.sh`: `74c2f2ab0720f96dea325229fe2abe565f78b55463571319e72e07ceae1fc4b7`
- `ci/conan/profiles/ohos-aarch64`: `63085cfa7a03f55f2c490939df0f924a73e08005ca77db1bd851ce2c2e08d18e`
- Recipe: `405d98ad2fb4469f16a1735f13a06f9fc8ef57008554d55072d9a10a2a38f530`
- Input verification record: `691cc719956173f0ac54fab0b50e44aa82f6b09872c9535b56346906f8c24ad3`
- Environment fingerprint: `28247e2860f93164cec36866744c8f88f6055e9338c99ee887114e8e69c4cd5f`
- Setup log: `438e3b95db723819b79cbf1d866ddeb3f42c29462d26b550b8633b4617b90bd0`
- Build log: `704681f4ab0ff935ee0cfed62ba08e6e6244aeb5d0fe0b45409445c9a3db5643`
- Gate results: `f1a804aa5fa1f577033041288442bf8609b13ccf5e9743a904330a1f4eac975e`

Preflight run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/f2707f8869c6-20260817T034404Z-preflight-37347`

Final run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/f2707f8869c6-20260817T034613Z-run-38240`

## Tests and gates

- 12 selected deterministic upstream CTests: pass (0 failed, 1.05 seconds)
- Conan `test_package`: pass; linked `SndFile::sndfile` and completed an actual
  WAV/PCM write, reopen, metadata, and exact-sample round trip
- Destructive negative test: pass; moving `lib/` and `include/` made the
  consumer test fail as required
- L0: pass, all checks passed
- L1: pass, upstream tests and `test_package` executed
- L2: skip, package intentionally has no `bin/` directory
- L4: pass, patches clean
- L5: pass, `lib/` has content

Created package:
`libsndfile/1.2.2#cf6ded313ae8c9c830e5ec3d3a8ce497:21b17f8b2bc0e9511e276e3d57a23893067cefe5#8975dac5b2a515db87a38e4255412d82`

## First-run diagnosis and repair

The first run tested commit
`e9cd83dc910129180508b6cae316f4a383153a48` and failed during the upstream
test build. Conan supplies a list-valued `CMAKE_MODULE_PATH`; upstream
`CMakeAutoGen.cmake` appended its script name to the full list and caused the
shell to attempt to execute the second path. The observed error was
`CMakeAutoGenScript.cmake: can't execute: Permission denied`.

Patch `0003-fix-cmake-autogen-module-path.patch` resolves the script relative to
`CMAKE_CURRENT_LIST_DIR`. The final run proved the repair by building the test
suite past the original 48 percent failure point and completing all gates.

Failed run:
`/storage/Users/currentUser/ohpc-ci-shadow/runs/e9cd83dc9101-20260817T033432Z-run-31272`

Failed-run evidence:

- Source archive: `c60b65f5cc580132d389d5edd764569a8578ecda76120e349b95213f5f434258`
- Input verification: `ee80eb7e2126579372063c84e0cc21b5aff9bdf21992c88f6910b8349481a17a`
- Environment fingerprint: `48ce6f576dde27d74ad455531765aa794ceba10ed1322821af80e84c278830f4`
- Setup log: `894dbe314b0431193ebefe5af1404528d1cd9c1294820e9526827c9676367b53`
