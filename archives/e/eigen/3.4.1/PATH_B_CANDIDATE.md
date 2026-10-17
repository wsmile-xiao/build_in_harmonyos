# eigen 3.4.1 Path B candidate evidence

This file records why the current `eigen@3` / `eigen/3.4.1` work can be
reviewed as a Path B knowledge-extension candidate. Final difficulty
classification remains a reviewer decision.

## Claim

The package recipe itself is not presented as novel or high-difficulty. The
already-published `eigen/3.4.1` recipe is intentionally kept unchanged to pass
R37. The Path B candidate claim is based on reusable knowledge extracted from
real OHOS shadow CI and from the eigen-specific validation boundary.

## Evidence

- Task library slot: `eigen@3`
- Conan package: `eigen/3.4.1`
- Worktree branch: `feat/eigen-3.4.1`
- Scope: `archives/e/eigen/3.4.1/` plus eigen-specific knowledge drafts.
- Source archive: `https://gitlab.com/libeigen/eigen/-/archive/3.4.1/eigen-3.4.1.tar.gz`
- SHA256: `b93c667d1b69265cdb4d9f30ec21f8facbbe8b307cf34c0b9942834c6d4fdbe2`
- Failed R37 runner:
  `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r1-20260828-100021-42976`
- Passing runner:
  `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r2-20260828-100610-44905`
- Passing shadow run:
  `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260828T020611Z-48f48aced7-44968`
- Passing commit in isolated repo: `48f48aced7`
- Shadow CI summary: `Total: 1`, `Success: 1`, `Failed: 0`
- Gates:
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: test_package executed`
  - `L2_RESULT=skip: no bin/ dir`
  - `L4_RESULT=pass: no patches`
  - `L5_RESULT=warn: no artifacts found`
- Runtime output: `eigen smoke test: PASS (matmul + norm OK)`.
- L1e destructive negative test passed: the consumer test failed when the
  packaged include path was removed.
- Installed package surface observed in the run:
  `include/eigen3/Eigen`, `include/eigen3/unsupported`,
  `share/eigen3/cmake`, `share/pkgconfig/eigen3.pc`.

## Draft knowledge added

- `knowledge/drafts/DRAFT-eigen-3.4.1-r37-published-recipe-collision.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-r37-published-recipe-collision.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-header-only-l5-evidence.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-header-only-l5-evidence.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-cmake-harmonyos-warning-triage.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-cmake-harmonyos-warning-triage.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-unsupported-threadpool-pthread-cancel-boundary.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-unsupported-threadpool-pthread-cancel-boundary.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-make-jobserver-mkfifo-nonfatal.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-make-jobserver-mkfifo-nonfatal.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-upstream-test-statistics-145.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-upstream-test-statistics-145.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-consumer-metadata-surface.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-consumer-metadata-surface.kv`
- `knowledge/drafts/DRAFT-eigen-3.4.1-test-package-negative-include-boundary.md`
- `knowledge/drafts/DRAFT-eigen-3.4.1-test-package-negative-include-boundary.kv`

## What this does not claim

- It does not claim a modified eigen recipe. `conanfile.py` and
  `conandata.yml` are kept unchanged because the same version is already
  published.
- It does not claim Path C or full upstream CTest execution.
- It does not claim all `unsupported/` Eigen modules are validated on OHOS.
  The current target runtime coverage is `<Eigen/Dense>` matrix multiplication
  and `Vector3d::norm()`.
- It does not claim that CMake `Platform/HarmonyOS` or make jobserver warnings
  are universally safe to ignore. The drafts only record the evidence boundary
  observed for this header-only package.
- It does not claim upstream Eigen's full `test/` tree ran on HarmonyOS. The
  inventory is recorded separately so reviewers can see the difference between
  upstream coverage scope and the consumer-only gate.

## Reviewer checklist

- Confirm only eigen-specific knowledge drafts are included.
- Confirm `archives/e/eigen/3.4.1/conanfile.py` and `conandata.yml` have no
  PR diff.
- Confirm shadow CI r2 metadata is available under the recorded remote run.
- Confirm the upstream Eigen test inventory is written as 145 `EIGEN_DECLARE_TEST`
  definitions, not 0.
- Decide whether the eight drafts are enough for B-class recognition, or should
  remain supplementary notes for a normal header-only adaptation.
