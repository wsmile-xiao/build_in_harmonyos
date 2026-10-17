# six 1.17.0 shadow CI report

## Result

- Date: 2026-08-19
- Device: HarmonyOS aarch64, `10.62.222.172:2222`
- Runner: `local-ohos-shadow-device1`
- Package: `archives/s/six/1.17.0`
- Commit: `2399ba25a8fae0c91f41552bbf6170881d7d03b1`
- Frozen input SHA256: `3509a4a37dfd45f54ae6774b361f5fe23754ab459c2894702b49f3f20d771d49`
- Preflight root: `/storage/Users/currentUser/ohpc-ci-shadow/runs/2399ba25a8fa-20260819T074008Z-preflight-52844`
- Run root: `/storage/Users/currentUser/ohpc-ci-shadow/runs/2399ba25a8fa-20260819T074009Z-run-52891`
- Status: PASS

## Gate summary

| Gate | Result | Detail |
|---|---|---|
| L0 | pass | all quality checks passed |
| L1 | pass | `test_package` executed |
| L2 | skip | pure Python library; no `bin/` directory |
| L4 | pass | no patches |
| L5 | pass | `lib/` contains packaged `six.py` |

Build summary: `Total: 1`, `Success: 1`, `Failed: 0`, pass rate `100.0%`.

## Functional evidence

The consumer test resolved `six.__file__` against the Conan package root and
exercised compatibility helpers and `six.moves.urllib.parse`:

```text
six 1.17.0 compatibility API: PASS
```

The L1e destructive check moved the packaged `lib/` directory away and
confirmed that the consumer test then failed. This proves the test depends on
the packaged module instead of the device's preinstalled six.

## Upstream tests

The unmodified upstream `test_six.py` was run locally from the
SHA256-verified sdist with pytest 8.4.2:

```text
201 tests collected
199 passed, 2 skipped, 0 failed
```

The two skips are controlled by upstream environment conditions.

## Reproducibility evidence

- Source SHA256: `ff70335d468e7eb6ec65b95b99d3a2836546063f63acc5171de367e834932a81`
- Setup log SHA256: `60d3437be8586a972eb62e69ba3812d6a0030b18bcfd37a3a15eb6a6f4f4deb8`
- Build log SHA256: `f9c2189f602608d517115162e564fbaff6d00bd38c01f46baf9c6581cd8ed219`
- Gate results SHA256: `6d9b8e0751ce62a741fc25e29c89b3526e779c19096458a327f878fe1d416447`
- Input verification SHA256: `ec8ff5a678d0b971f40ec4c820acf66c281f04d9c4b7a11923d56dad8cadd9d6`
- Environment fingerprint SHA256: `7c60b5156250ce3c8e941c447b8559117d9b7af958689b32d29850a4bbaab32f`

The device used Python 3.12.9 and Conan 2.29.1.

## Earlier attempts

1. The first run stopped in setup because the frozen input omitted the new
   `ci/conan/sqlite_runtime.sh` helper. The recipe did not run.
2. The second run reached L0 and identified missing `compiler` and
   `build_type` settings. Commit `2399ba25a8` added the required declarations.
