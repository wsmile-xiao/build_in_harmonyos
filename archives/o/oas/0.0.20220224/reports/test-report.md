# oas 0.0.20220224 test report

## Counting method

The common unit is a logical test case. Upstream ships no test suite at all, so the upstream row is measured by scanning the release archive's build inputs (the counting command and its zero-hit reading are recorded in `notes.md` §3). The consumer side is `test_package/test.c`, where each independently described scenario checked by `check(...)` is one case; assertion-level output is quoted from the CI-simulation log rather than counted by hand.

## Results

| Environment | Test group | Passed | Failed | Skipped | Assertions | Result |
|---|---|---:|---:|---:|---:|---|
| HarmonyOS PC aarch64, conan create + CI simulation (rerun5, 2026-09-25 23:00) | Upstream test suite | 0 | 0 | 0 | 0 (no upstream suite exists) | n/a |
| HarmonyOS PC aarch64, packaged consumer (`test_package`) | API scenarios | 4 | 0 | 0 | 4 | PASS |

Machine-readable evidence, by line in `reports/w3-local-ci.log` (341 lines, `md5 f973fc85648c626dd73a759fcf775e26`):

- `:306` `ok null address returns the no-match sentinel (value=10000)`
- `:307` `ok v6 address returns sentinel or a positive rule number (value=10000)`
- `:308` `ok same address scores identically twice (value=10000)`
- `:309` `ok liboas.so exports oas_address_score (value=1)`
- `:310` `PASS all 4 assertions`
- `:312` `[ok] oas/0.0.20220224 — conan create passed`
- `:314` `[ok] L1a: test_package was executed by conan create`, `:315` `[ok] L1b: Test execution evidence found in log`, `:316` `[step] L1c: No upstream make check/ctest in log (may be in test_package only)`, `:323` `[ok] L1e: Negative test confirmed — test genuinely depends on oas`
- `:327`–`:331` quality-gate machine lines: `L0 pass`, `L1 pass`, `L2_RESULT=skip: no bin/ dir`, `L4 pass`, `L5_RESULT=pass: lib/ has content`
- `:337`–`:339` `Success: 1`, `Failed: 0`, `Pass rate: 100.0% (1/1)`

`.ci-result.json` carries `exit_code: 0` with `log_sha256` equal to the independently recomputed `sha256sum` of that log (`e4e581f0…27ac4d`).

## Consumer scenarios

1. `oas_address_score(NULL)` returns the documented no-match sentinel `10000`.
2. `oas_address_score()` on a real `sockaddr_in6` returns the sentinel **or** a positive rule number (disjunctive check).
3. Two calls with the same address return the same score.
4. `dlsym` on the installed `liboas.so` resolves the exported symbol `oas_address_score`.

## Strength of the evidence, stated plainly

- With no oas rule set loaded in this environment, the three runtime readings above are all the sentinel value `10000`, so scenario 3 compares two sentinel values and the "positive rule number" branch is **not distinguished**. Scenarios 1 and 4 are the discriminating ones. This is stated rather than glossed over: an implementation that always returned `10000` would satisfy all four checks. It is not a false-positive risk in the other direction: `check()` increments a failure counter on every else branch and `main` prints `FAILED` and returns 1 when it is non-zero, so a skipped assertion cannot be recorded as a pass.
- `connect()` interposition — the other half of this library's feature surface — is **not exercised** by `test_package`. See `notes.md` §3 and the PR body's known limitations for the measured basis (`test.c` is 56 lines, `grep -c -i connect` is 0, the single `dlsym` site is at `test.c:45`).
- `L2` smoke test is skipped by design (library package, no `bin/`), so it is neither a failure nor evidence of runnability.
- Framework gate `G4` is a **downgraded PASS** (its artifact-integrity check did not execute); artifact completeness is therefore evidenced by the manual per-file `readelf -d` readings in `notes.md` §12.6, not by `G4`.
