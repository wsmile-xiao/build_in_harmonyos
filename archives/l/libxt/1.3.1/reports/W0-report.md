# libXt 1.3.1 W0 report

Date: 2026-08-21 (Asia/Hong_Kong)

## Result

`PASS_CURRENT_CANDIDATE`

The provider-publication blocker remains cleared. Fresh W0 resolves
all five direct references and their complete OHOS/arm64 graphs with
`--build=never`; no missing dependency is built locally.

## Bound inputs

- Candidate base HEAD: `22b865bd938c002b4118bba57613628ddadeaf7a`.
- The final staged tree is bound by the external W3/W4 evidence.
- Current main: `8e0d2cbf322ca9d9a5b271f80cb82c66be2af166`.
- Branch: `feat/libxt-1.3.1`.
- Host/build profile: OHOS 6.0, armv8, clang 15, Release.
- Conan client: community OHOS-adapted Conan 2.29.1.
- Remote: `ohpcd` at
  `https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/`.
- Resolution policy: `--build=never`, `download_parallel=1`, and a fresh
  task-private Conan home under `F:/HarmonyPC`.
- Evidence root: `F:/HarmonyPC/openj9-1084/libxt-final-20260821` (the exact successor run is recorded externally).

## Validated result

- Direct references: 5/5 recipe download and install RC0.
- Graphs: 5.
- Node occurrences: 21.
- Unique RREV/PID/PREV identities: 14.
- Materialized binaries downloaded from `ohpcd`: 9 identities.
- Skip-only graph identities: 5; each has an exact recipe revision and empty
  `info_invalid`, without inventing a package-folder requirement.
- Validator failures: none.

This is dependency-resolution evidence only. The exact candidate also passed
device W3 with 16 PASS plus 4 exact expected SKIP for all 20 upstream paths;
both independent consumers passed in shared and static profiles. Its final tree
identity and W4/Pre-PR evidence remain separate external records.

## Resume condition

Preserve the exact RREV/PID/PREV identities on any future provider or main
drift. Do not replace `--build=never`, count skip-only identities as materialized
binaries, or reuse a predecessor run after a software-input change.
