# eigen 3.4.1 pre-adaptation notes

## Status
- Date: 2026-08-28
- Task library slot: `eigen@3`
- Conan package: `eigen/3.4.1`
- Branch/worktree: `feat/eigen-3.4.1` at `D:\harmonyos\worktrees\eigen`
- Scope: only `archives/e/eigen/3.4.1/`
- Current state: shadow CI passed; same-version recipe kept unchanged because `eigen/3.4.1` is already published
- Issue: intentionally ignored for this round per user direction
- Path B status: candidate only; see `PATH_B_CANDIDATE.md` and the eigen-specific drafts under `knowledge/drafts/`

## W0 dependency check
- Conan dependencies: none
- Build-system dependencies: CMake only
- `python scripts/ohc-run.py resolve-deps eigen 3.4.1`: passed
- No missing dependency library needs to be split out.

## Source and build-system analysis
- Source URL: `https://gitlab.com/libeigen/eigen/-/archive/3.4.1/eigen-3.4.1.tar.gz`
- Verified SHA256: `b93c667d1b69265cdb4d9f30ec21f8facbbe8b307cf34c0b9942834c6d4fdbe2`
- Upstream version header: `EIGEN_WORLD_VERSION=3`, `EIGEN_MAJOR_VERSION=4`, `EIGEN_MINOR_VERSION=1`
- Build system: top-level CMake project `Eigen3`
- Package shape: header-only install of `Eigen/` and `unsupported/`, CMake package `Eigen3::Eigen`, pkg-config name `eigen3`

## Conan recipe choices
- `eigen/3.4.1` is already present in the Conan registry; R37 rejects same-version recipe changes.
- Keep `conanfile.py` and `conandata.yml` byte-for-byte unchanged from the existing archive entry.
- Existing recipe uses `CMakeToolchain`; configure/install runs with optional targets disabled, and there is no compiled library target for the header-only package.
- Existing recipe disables:
  - `BUILD_TESTING=OFF`
  - `EIGEN_BUILD_BLAS=OFF`
  - `EIGEN_BUILD_LAPACK=OFF`
  - `EIGEN_BUILD_DOC=OFF`
  - `EIGEN_BUILD_PKGCONFIG=ON`

## Test package
- Consumer build uses Conan `CMakeDeps`, `CMakeToolchain`, and `VirtualRunEnv`.
- `test.cpp` includes `<Eigen/Dense>`, verifies 2x2 matrix multiplication, and checks `Vector3d::norm()`.
- Assertion count: 2.
- If OHOS CI worker refuses to execute a non-system binary with `Operation not permitted` / `Error 126`, the test logs an explicit skip message and leaves runtime verification for the device queue.

## Upstream test inventory
- Eigen `test/` contains 148 `.cpp` files and 145 `EIGEN_DECLARE_TEST` definitions.
- For PR reporting, the upstream unit-test tally should be written as 145, not 0, even when the shadow gate only executes the consumer `test_package`.
- Keep the upstream inventory separate from the consumer pass rate.

## Local validation performed
- Source tarball downloaded and SHA256 matched `conandata.yml`.
- Source archive structure inspected: top-level `CMakeLists.txt`, `CTestConfig.cmake`, `Eigen/`, `unsupported/`, `test/`, `bench/`, `blas/`, `lapack/`.
- Python syntax parse of recipe files passed.
- Upstream pre-scan command:
  - `python scripts/ohc-run.py prescan --no-writeback --json <extracted eigen-3.4.1 source>`
- Pre-scan findings and handling:
  - `pthread_cancel` in `unsupported/Eigen/CXX11/src/ThreadPool/ThreadCancel.h`: not exercised by the smoke test; mark for device/runtime attention if unsupported ThreadPool is used by downstreams.
  - bash shebangs under `bench/`, `ci/`, `blas/testing/`, and scripts: avoided by disabling tests, BLAS/LAPACK, and docs in the existing recipe.
  - glibc guards in core/special-functions headers: conditional code already guarded by `__GLIBC__`; no OHOS patch applied during preflight.

## Shadow CI attempt 1
- Outer runner: `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r1-20260828-100021-42976`
- Inner shadow run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260828T020023Z-1a9b11bd4b-43039`
- Result: failed in L0 before build/test.
- Reason: `eigen/3.4.1` is already published with a different recipe, and the first attempt included a local `conanfile.py` change.
- Follow-up: restored `conanfile.py` to the published archive entry and rerun shadow CI without same-version recipe changes.

## Shadow CI validation
- Outer runner: `/storage/Users/currentUser/ohos-test-runs/codex-eigen-eigen-eigen-3.4.1-C0DX-shadow-r2-20260828-100610-44905`
- Inner shadow run: `/storage/Users/currentUser/ohpc-ci-shadow/runs/20260828T020611Z-48f48aced7-44968`
- Source commit in isolated repo: `48f48aced7`
- Result: pass, `Total: 1`, `Success: 1`, `Failed: 0`
- Gate summary:
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: test_package executed`
  - `L2_RESULT=skip: no bin/ dir`
  - `L4_RESULT=pass: no patches`
  - `L5_RESULT=warn: no artifacts found`
- `test_package` built and executed `test_eigen`.
- Runtime output: `eigen smoke test: PASS (matmul + norm OK)`.
- L1e destructive negative test passed: removing packaged includes caused the consumer test to fail as expected.
- L5 warning is expected for a header-only package with no `bin/` or `lib/`; package output contains `include/eigen3/Eigen`, `include/eigen3/unsupported`, `share/eigen3/cmake`, and `share/pkgconfig/eigen3.pc`.

## Path B candidate knowledge drafts
- `PATH_B_CANDIDATE.md` records the review boundary: this is a knowledge-extension candidate, not a claim of recipe novelty or Path C coverage.
- `knowledge/drafts/DRAFT-eigen-3.4.1-r37-published-recipe-collision.md`: same-version R37 collision; keep published `conanfile.py` and `conandata.yml` unchanged unless a suffix version is required.
- `knowledge/drafts/DRAFT-eigen-3.4.1-header-only-l5-evidence.md`: how to close L5/no-binary warnings for a header-only Eigen package with include, CMake, pkg-config, target runtime, and destructive negative-test evidence.
- `knowledge/drafts/DRAFT-eigen-3.4.1-cmake-harmonyos-warning-triage.md`: when CMake `Platform/HarmonyOS` warning is non-blocking for Eigen's header-only consumer path, and when to escalate to existing CMake platform knowledge.
- `knowledge/drafts/DRAFT-eigen-3.4.1-unsupported-threadpool-pthread-cancel-boundary.md`: pre-scan `pthread_cancel` in `unsupported/` is a downstream ThreadPool/Tensor boundary, not covered by the Dense smoke test.
- `knowledge/drafts/DRAFT-eigen-3.4.1-make-jobserver-mkfifo-nonfatal.md`: make jobserver FIFO warning was non-fatal in this tiny CMake consumer build because the target built and executed.
- `knowledge/drafts/DRAFT-eigen-3.4.1-upstream-test-statistics-145.md`: how to report Eigen's upstream `test/` inventory without collapsing the count to zero when only the consumer gate runs.
- `knowledge/drafts/DRAFT-eigen-3.4.1-consumer-metadata-surface.md`: header-only packages should record the installed include tree and generated consumer metadata together.
- `knowledge/drafts/DRAFT-eigen-3.4.1-test-package-negative-include-boundary.md`: destructive negative test boundary for proving the consumer really depends on the packaged headers.
- Matching `.kv` metadata drafts were added beside each `.md` draft for later reviewer promotion.

## Not run locally
- `conan create` / `ohc-run.py conan-verify`: not run because local PATH has no `conan`.
- CMake configure/build: not run because local PATH has no `cmake` or C++ compiler.
- Local host did not run target binaries; OHOS shadow CI covered the Conan create and runtime test.

## Next verification commands
```sh
CI_PACKAGES="archives/e/eigen/3.4.1" zsh ci/conan/build_and_test.sh
```

Optional project wrapper when the OHOS validation environment has Conan/CMake configured:

```sh
python3 scripts/ohc-run.py conan-verify eigen 3.4.1
```

Expected validation focus:
- Confirm CI discovers exactly one package: `archives/e/eigen/3.4.1`.
- Confirm CMake install lays down `include/eigen3/Eigen`, `include/eigen3/unsupported`, `share/eigen3/cmake`, and `share/pkgconfig/eigen3.pc`.
- Confirm `test_package` compiles `test_eigen`; run it on a device/shadow worker where non-system executable policy permits it, or record the explicit exec-policy skip.
- For Path B review, confirm the knowledge drafts remain eigen-specific and do not overclaim unsupported Eigen modules or full upstream CTest coverage.
