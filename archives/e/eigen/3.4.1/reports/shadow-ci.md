# eigen 3.4.1 shadow CI report

Date: 2026-08-28

## Input
- Worktree: `D:\harmonyos\worktrees\eigen`
- Remote isolated job: `/storage/Users/currentUser/ohos-users/codex-eigen/eigen-3.4.1-C0DX-shadow-r1`
- Remote source commit: `48f48aced7`
- Package path: `archives/e/eigen/3.4.1`
- Source SHA256: `b93c667d1b69265cdb4d9f30ec21f8facbbe8b307cf34c0b9942834c6d4fdbe2`
- Toolchain: Conan 2.29.1, CMake 4.1.2, clang 15.0.4, HarmonyOS aarch64

## Commands
```sh
. /storage/Users/currentUser/ohos-users/codex-eigen/eigen-3.4.1-C0DX-shadow-r1/env.sh
cd "$CI_REPO_ROOT"
export SHADOW_SOURCE_COMMIT=48f48aced7
sh "$HOME/bin/ohos-test-runner.sh" \
  --user codex-eigen \
  --lib eigen \
  --task eigen-3.4.1-C0DX-shadow-r2 \
  --mode smoke \
  --try-lock \
  --path "$HOME/usr/local/bin:$HOME/.local/bin:$HOME/ohpc-ci-shadow/python-user/bin:/data/service/hnp/bin:/data/service/hnp/cmake.org/cmake_4.1.2/bin" \
  --workdir "$CI_REPO_ROOT" \
  -- sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/e/eigen/3.4.1
```

## Result
- Outer runner: `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r2-20260828-100610-44905`
- Inner shadow run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260828T020611Z-48f48aced7-44968`
- Exit code: 0
- Build summary: `Total: 1`, `Success: 1`, `Failed: 0`

## Gates
```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=warn: no artifacts found
```

`L5` is a warning because Eigen is header-only and installs no `bin/` or `lib/`
content. The package folder contains `include/eigen3/Eigen`,
`include/eigen3/unsupported`, `share/eigen3/cmake`, and
`share/pkgconfig/eigen3.pc`.

## Test Evidence
```text
eigen smoke test: PASS (matmul + norm OK)
L1e: Negative test confirmed - test genuinely depends on eigen
```

Full package reference:

```text
eigen/3.4.1#e0bffc688f1af265318e922a01f76dec:6b129b068851896169fae42d399fa922d239ce8a#44eba429826ca8098f6398ebd8e2d40e
```

## First Attempt
The first shadow run stopped in L0 with `version_not_incremented` because
`eigen/3.4.1` is already published and the initial local input changed
`conanfile.py`. The recipe was restored to the published archive entry before
the passing r2 run.
