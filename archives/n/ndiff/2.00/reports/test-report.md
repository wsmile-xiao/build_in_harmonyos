# Test Report - ndiff 2.00

## Environment

- Platform: HarmonyOS PC, OHOS 6.0, armv8/aarch64
- Compiler: clang 15 from the OHOS Conan profile
- Conan: 2.29.1
- Package reference: `ndiff/2.00@ohpcd/stable`

## Commands

```bash
python3 scripts/ohc-run.py conan-verify ndiff 2.00
python3 scripts/ohc-run.py finish ndiff 2.00 built
```

During Conan build, the recipe ran the upstream suite with:

```bash
make check -j1 TMPDIR=<build_folder>/check-tmp LN=cp
```

The consumer test was run by Conan with:

```bash
bash test.sh
```

## Test Summary

| 项目 | 数量 | 说明 |
|------|------|------|
| 总测试数 | 31 | 26 upstream `make check` cases + 5 consumer assertions |
| 通过 PASS | 31 | W3 local CI and conan-verify both passed |
| 失败 FAIL | 0 | No failed upstream or consumer tests |
| 跳过 SKIP | 0 | No skipped tests |

## Upstream Tests

The upstream `make check` suite executed `check001` through `check026`.
It covered option parsing, version/help commands, field selection, quiet/silent
modes, absolute-error thresholds, relative-error thresholds, normal differences,
and web output behavior. The suite passed with the native long-double precision
build.

## Consumer Tests

`test_package/test.sh` verified the installed package from a consumer context:

- `ndiff --version` prints `Version 2.00`.
- A relative-error tolerance of `1e-3` accepts a small numeric difference.
- A relative-error tolerance of `1e-9` rejects the same pair.
- The out-of-tolerance report contains `relative error`.
- The out-of-tolerance report contains the differing value `1.000001`.

## Result

PASS. `conan-verify` passed G0/G1/G2/G3/G4 and W3 local CI passed with
`L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=pass`, `L4_RESULT=pass`, and
`L5_RESULT=pass`.

## Known Limitations

None.
