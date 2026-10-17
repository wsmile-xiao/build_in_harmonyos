# Draft: test-framework self-test suites deliberately fail by design — the recipe build() upstream-test gate must follow upstream harness semantics

> Source event: cheat/1.0.4 adaptation, 2026-09-19.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

A unit-testing framework's own test suite MUST contain negative-path cases
— assertion deliberately false, crash/signal injection, output over-limit,
random asserts — to prove the framework can detect and report failures.
Those binaries exit `rc=1` with a `FAILURE` report, and that is the
expected product, not a defect:

```text
tests/failed.c:4: assertion in 'failure' failed: 'false'
1 failed of 1 run
FAILURE
```

Upstream harnesses encode this intent explicitly:

- `makefile` `test` target: `- ./example -s` (the leading `-` tells make to
  ignore the failing recipe line);
- `test` script: runs `"$o" $1` and never checks `$?`.

A recipe `build()` that treats any non-zero test exit as a gate failure
will therefore fail on a perfectly healthy upstream suite — misclassifying
every by-design negative-path case.

## Measured facts (cheat 1.0.4, OHOS aarch64)

- 25/25 `tests/*.c` files compile with the OHOS clang (with
  `-D_POSIX_C_SOURCE=200112L`); 25/25 run and print a framework report.
- Of 46 framework-level runs: 26 report FAILURE (24 CHEAT_TEST negative
  path + 2 CHEAT_REPEAT random asserts) — all upstream by-design; the
  suite's purpose is to verify failure/crash reporting.
- Gate design: compile = hard gate; run = require the framework report
  (`SUCCESS`/`FAILURE`/`N ... of K run`), rc<=127 with report = fine,
  rc>=128 (crash outside the framework) or missing report = run failure.
- `conan-verify cheat 1.0.4`: G1–G4 PASS; W3 local CI: JC/L0/L1 pass,
  pass rate 100% (1/1).

## Recommended approach

In the recipe `build()`, compile every upstream test file (compile failure
= real platform defect = hard gate), then run each binary and require only
that it produced the framework's report output. Treat rc<=127 with a
report as executed-and-fine; flag rc>=128 (unhandled crash) or missing
report as a run failure. In the test ledger, list the negative-path cases
with their by-design reason and the strict pass-rate
(`executed_passed/source_declared`) plus the executed-set rate.

```bash
for i in tests/*.c; do
  cc -D_POSIX_C_SOURCE=200112L -I . -o prog -w "$i" || exit 1   # hard gate
  ./prog -s                                                      # report required, rc informational
done
```

## Forbidden shortcuts

- Treating every non-zero exit as gate failure (misclassifies by-design
  negative-path cases; healthy frameworks never pass).
- Skipping the upstream suite to dodge negative-path cases (hides real
  compilation regressions).

## Related

- `similar_to`: E370 (test-counting honesty for platform-conditioned
  fixtures), DRAFT-box2d-2.4.1-ctest-empty-suite-false-pass (empty-suite
  false pass). This entry is the negative-path/exit-code-semantics variant.
