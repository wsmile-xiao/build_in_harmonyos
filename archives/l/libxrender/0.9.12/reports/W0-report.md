# libxrender 0.9.12 W0 report

Date: 2026-08-19 (Asia/Hong_Kong)

## Result

`PASS`

Fresh isolated shared and static `conan graph info` and `conan install` runs
all returned zero with `--build=never`. Each graph has nine nodes and eight
dependencies, no `Missing` binary, and no non-empty `info_invalid`. No source
fallback was allowed.

## Bound inputs

- Repository base: `f06dafbfc326bbbaf1bfcd423abe72b43dcf1654`.
- Candidate HEAD: `7c9b04980cce274df7f432baa6a0b43cd2e82bc7`.
- Candidate branch: `feat/libxrender-0.9.12`.
- Host/build profile: OHOS 6.0, armv8, clang 15, Release.
- Conan client: community OHOS-adapted Conan 2.29.1.
- Remote: `ohpcd` at
  `https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`.
- Resolution policy: `--build=never` in a fresh F-drive Conan home with
  `conancenter` disabled.
- Durable evidence:
  `E:/HarmonyPC/validation/libxrender-0.9.12/w0-20260819-r12`.
- Evidence `SHA256SUMS`: verified with zero mismatches.

## Shared/static contract

- Shared toolchain: exactly one `--enable-shared`, exactly one
  `--disable-static`, and neither static-mode switch.
- Static toolchain: exactly one `--disable-shared`, exactly one
  `--enable-static`, and neither shared-mode switch.
- Both modes resolve the same eight RREV/PID/PREV tuples.
- Both root nodes report the expected package type: `shared-library` and
  `static-library`, respectively.

## Direct dependencies

### xorgproto/2025.1

The package installed successfully from `ohpcd`:

- RREV: `f5274e33759da898a6e8d87d7708d47c`
- Package ID: `283a988d63e011a731408b6abe0950de49e6171d`
- PREV: `b7dc443b533634631c412ae235a57198`
- Binary state: `Download`
- Binary remote: `ohpcd`
- `info_invalid`: empty

### libx11/1.8.13

The package installed successfully from `ohpcd`:

- RREV: `e3ce69008a37ca95d1f0918c47709057`
- Package ID: `cae7d429fb6839b6840b7602f11bf20c76efecdf`
- PREV: `701e81816807aea0ad862a324557f4e9`
- Binary state: `Download`
- Binary remote: `ohpcd`
- `info_invalid`: empty

The six transitive dependency nodes are recorded with the two direct nodes in
`identity-summary.json`; every node has RREV/PID/PREV,
`binary_remote=ohpcd`, and empty `info_invalid`.

## Resume condition

W0 is closed. The same candidate subsequently completed exact-snapshot W3 r11
and the official finish W3 substep in r27. Those later results remain separate
from this dependency-resolution report.
