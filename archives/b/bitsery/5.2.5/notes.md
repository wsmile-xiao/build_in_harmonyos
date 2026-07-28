# bitsery 5.2.5 adaptation notes

## Scope

- Issue: #1578
- Worktree: `D:\harmonyos\worktrees\bitsery`
- Branch: `feat/bitsery-5.2.5`
- Adaptation path: `archives/b/bitsery/5.2.5`

## W0 Dependency Check

- bitsery is header-only and its README documents C++11 compiler support as the main requirement.
- Mandatory library dependencies: none.
- Optional upstream test dependency: GTest 1.10. `conan download "gtest/1.10.0" -r=ohpcd --only-recipe` could not complete because the ohpcd remote returned `system acceleration policy not enabled`; do not mix a GTest adaptation into this PR.
- `conan search "bitsery*" -r=ohpcd` found no existing bitsery recipe, so this package remains an unpublished target for this PR.

## Source And Build System

- Source URL: `https://github.com/fraillt/bitsery/archive/refs/tags/v5.2.5.tar.gz`
- SHA256: `22a6d92ac030e999b53d57a0c9afe28723766595c6d00c91ab9c5637d4ed0eec`
- Upstream build system: CMake interface/header-only target.
- Recipe strategy: copy `include/bitsery` and `LICENSE` directly; set Conan CMake properties to expose `Bitsery::bitsery`.
- Patches: none.

## Test Strategy

- Upstream GTest-based tests are recorded in `test_package/MANIFEST.yml`; they are not integrated into `build()` because GTest is not an ohpcd-published dependency for this PR.
- Upstream tests were completed on the isolated OHOS device by temporarily building GTest 1.15.2 inside the job `work/` directory and running upstream `ctest`.
- `test_package/test_bitsery.cpp` performs a real consumer smoke test: serialize and deserialize a struct with integer, string, and vector fields, then verify the round-trip data.

## Local Verification

Commands attempted:

```powershell
conan --version
conan search "bitsery*" -r=ohpcd
conan download "gtest/1.10.0" -r=ohpcd --only-recipe
```

Results:

- Conan version: 2.29.1.
- ohpcd contains no matching `bitsery*` recipe.
- GTest recipe download check was blocked by the ohpcd acceleration-policy error.
- GitHub source download from this Windows host timed out, so full `conan create` was not run locally.

## OHOS Device Verification

Isolation job:

```text
/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5
```

Confirmed isolation before the successful build:

- `CONAN_HOME=/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5/conan-home`
- `CI_REPO_ROOT=/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5/repo/build_in_harmonyos`
- `CI_PACKAGES=archives/b/bitsery/5.2.5`
- Global device lock was free and was acquired by the runner with `wait_seconds=0`.
- Build did not use default `$HOME/.conan2` or shared `$HOME/validation/build_in_harmonyos`.

Initial isolated run failed because the new private Conan home had a stale/default `settings.yml` without the `OHOS` enum. Fixed by copying the OHOS-aware default `settings.yml` and `remotes.json` into the private `CONAN_HOME`, then running `zsh ci/conan/setup.sh` in the isolated environment.

Successful run:

```text
run_id=codex-bitsery-5.2.5-bitsery-5.2.5-conan-20260727-221956-50978
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-bitsery-5.2.5-bitsery-5.2.5-conan-20260727-221956-50978
exit_code=0
```

Results:

- `conan create` passed.
- Packaged `LICENSE` and 62 header files.
- `test_package` built and executed `./test_bitsery`.
- Runtime output: `bitsery round-trip test passed, bytes=27`.
- `L0_RESULT=pass`
- `L1_RESULT=pass`
- `L2_RESULT=skip` because this is a header-only library with no `bin/`.
- `L4_RESULT=pass`
- `L5_RESULT=warn` because this package has no `bin/` or `lib/` artifacts; headers were packaged successfully.
- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`.

## Upstream Test Verification

Upstream test run used the same isolated job and global-lock runner:

```text
run_id=codex-bitsery-bitsery-upstream-ctest-20260727-223047-56317
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-bitsery-bitsery-upstream-ctest-20260727-223047-56317
exit_code=0
```

Command summary:

```sh
cmake -S "$SRC" -B bitsery-build \
  -DBITSERY_BUILD_TESTS=ON \
  -DBITSERY_BUILD_EXAMPLES=OFF \
  -DCMAKE_PREFIX_PATH="$GTEST_PREFIX" \
  -DCMAKE_CXX_FLAGS="-Wno-unused-command-line-argument"
cmake --build bitsery-build --parallel 1
ctest --test-dir bitsery-build --output-on-failure -j1
```

Results:

- Temporary test dependency: GTest 1.15.2 built inside `/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5/work/upstream-tests/gtest-prefix`.
- Upstream test source files: 32 files under `tests/*.cpp`.
- Discovered CTest cases: 360.
- CTest summary: `100% tests passed, 0 tests failed out of 360`.
- Total test time: `10.11 sec`.
- No upstream source or test files were modified.

## Next Commands

Single-package shadow CI, when the device or shadow runner is available:

```sh
CI_PACKAGES="archives/b/bitsery/5.2.5" zsh ci/conan/build_and_test.sh
```

Alternative shadow runner:

```sh
/path/to/run-ohos-shadow-ci.sh archives/b/bitsery/5.2.5
```

Manual Conan verification on an OHOS worker with source-network access:

```sh
cd archives/b/bitsery/5.2.5
conan create . --user=ohpcd --channel=stable -pr:h=$HOME/.conan2/profiles/ohos -pr:b=$HOME/.conan2/profiles/ohos --build=missing
```
