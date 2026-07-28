# bitsery 5.2.5 OHOS device build report

## Isolation

- Job base: `/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5`
- Private Conan home: `/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5/conan-home`
- Private repo: `/storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5/repo/build_in_harmonyos`
- Target package: `archives/b/bitsery/5.2.5`
- Runner mode: `heavy`, global lock acquired with `wait_seconds=0`

## Command

```sh
sh /storage/Users/currentUser/ohos-users/codex-bitsery/bitsery-5.2.5/run-conan-heavy.sh
```

## Successful Run

```text
run_id=codex-bitsery-5.2.5-bitsery-5.2.5-conan-20260727-221956-50978
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-bitsery-5.2.5-bitsery-5.2.5-conan-20260727-221956-50978
exit_code=0
```

## Results

- `conan create` passed.
- Package contents: `LICENSE` plus 62 bitsery header files.
- `test_package` built with CMake and executed `./test_bitsery`.
- Test output: `bitsery round-trip test passed, bytes=27`.
- Build Summary: `Total: 1`, `Success: 1`, `Failed: 0`.

CI result lines:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: no patches
L5_RESULT=warn: no artifacts found
```

`L2 skip` and `L5 warn` are expected for this header-only package: it produces headers, not executable or library artifacts.

## Upstream Tests

```text
run_id=codex-bitsery-bitsery-upstream-ctest-20260727-223047-56317
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-bitsery-bitsery-upstream-ctest-20260727-223047-56317
exit_code=0
```

- Temporary GTest 1.15.2 was built inside the isolated job `work/` directory.
- Upstream test files: 32 `tests/*.cpp` files.
- CTest cases: 360.
- Result: `100% tests passed, 0 tests failed out of 360`.
- Total CTest time: `10.11 sec`.
- No upstream test source files were modified.
