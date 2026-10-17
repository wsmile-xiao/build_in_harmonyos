# libfacedetection 3.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC real device (HongMeng Kernel 1.12.0, aarch64)
- Clang 15.0.4 (LLVM)
- CMake 4.1.2
- Conan 2.30.0

## Verification

- `ohc-run.py conan-verify libfacedetection 3.0`: exit 0 — G0/G1/G2/G3/G4 PASS
- `conan create` (ohos-aarch64 profile, `--build=missing`): exit 0
- W3 local CI simulation (`setup.sh` + `build_and_test.sh`): PASS (with JC pr.diff
  scoped isolation for pre-existing main-baseline junk files from other
  libraries — see isolation audit below)
- L0 quality gates: passed (L0a-L0m; no CLI, no commands.json needed)
- L1 test_package: PASS (1/1 test_libfacedetection)
- L2 platform smoke: PASS (test binary runs natively on HarmonyOS PC aarch64)
- L4 static security scan: PASS
- L5 product baseline: PASS

## test_package

The consumer test constructs a 256x192 blank BGR image, calls the library
`facedetect_cnn()` API with a 0x20000-byte result buffer, asserts the API
returns a valid result pointer with a non-negative face count, and exits 0.

- Test cases: 1 (assertions: 3 — non-null result, non-negative count, exit 0)
- Result: PASS (0 faces detected on blank image, API contract verified)

## Upstream test inventory (R51)

libfacedetection 3.0 has **no upstream test suite**: the top-level
CMakeLists.txt registers no ctest (`enable_testing`/`add_test` absent); the
`example/` directory only contains OpenCV-dependent demo programs
(detect-image/detect-camera/benchmark) gated behind `DEMO=ON`, which are not
library runtime dependencies and are excluded from the recipe build.

## Isolation / recovery audit (unrelated historical baseline)

While running W3 `build_and_test.sh` in its default full-repo junk-check mode,
the JC (junk check) gate flagged 3 tracked runtime-state files that belong to
**other libraries and already exist in the `main` baseline** (committed by
their own PRs):

| path | owner lib | owner commit | tracked in main | sha256 |
|---|---|---|---|---|
| archives/c/cloog/0.21.1/.build-closed | cloog | 906cc59ae7 | yes (empty) | e3b0c44…b855 |
| archives/c/cloog/0.21.1/.staging-verified | cloog | 906cc59ae7 | yes (empty) | e3b0c44…b855 |
| archives/k/kics/2.1.20/.staging-verified | kics | d9489aee83 | yes (empty) | e3b0c44…b855 |

None of these paths is inside this task's `delivery_allowed_paths`
(`archives/l/libfacedetection/3.0/**`). They were **not modified, deleted, or
staged** by this task. The real CI runs the junk check in `prdiff` mode (only
the PR's own file list), so these main-baseline files would not block this PR.
To replicate the CI-equivalent check locally before the branch is pushed, a
temporary `pr.diff` containing only this task's changed files was generated
(intent-to-add + `git diff -- archives/l/libfacedetection/`), the W3 gate was
re-run with `JUNK_PR_DIFF` pointing at it, and the gate passed
(JC_RESULT=pass, JC_ERRORS=0). The temporary pr.diff was removed afterwards —
**no persistent changes to repo state**. Full audit JSON:
`.atomcode/ohpc-state/libfacedetection-jc-baseline-isolation.json`.
