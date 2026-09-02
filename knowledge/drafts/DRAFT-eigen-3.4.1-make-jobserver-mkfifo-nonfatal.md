# Draft: eigen make jobserver mkfifo non-fatal signal

> Source event: `eigen/3.4.1` OHOS shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

The OHOS shadow run printed a make jobserver FIFO warning:

```text
make: jobserver mkfifo: ... Operation not permitted
```

This message can be alarming because it also appears in complex upstream test
migrations where parallel make or the filesystem really does block progress.
In the eigen run it was non-fatal: make fell back, the consumer target built,
and the test binary executed successfully.

## Recommended triage

When this warning appears during a small CMake `test_package` build:

1. Check the exit code and whether the requested target was produced.
2. Check whether CMake or make continued after the warning.
3. Check runtime evidence before classifying the warning as a blocker.
4. If the build fails or hangs, rerun with serialized make or CMake build
   parallelism disabled.
5. Do not add package source patches for the warning unless the package itself
   owns the failing parallel build behavior.

## Evidence from eigen

The passing r2 run completed with:

- `L1_RESULT=pass: test_package executed`
- `test_package` built `test_eigen`
- runtime output: `eigen smoke test: PASS (matmul + norm OK)`
- final summary: `Total: 1`, `Success: 1`, `Failed: 0`

The warning therefore remained an environment/build-tool note, not an eigen
source compatibility issue.

## Relation to existing knowledge

Existing knowledge records make jobserver FIFO issues in larger C++ test
migrations. This draft adds the eigen-specific decision boundary for tiny
consumer builds: the warning can be non-fatal if the target is built, executed,
and the CI summary is green.

## Boundaries

This is not permission to ignore all jobserver warnings. Treat it as a
non-blocking signal only when the build command exits successfully and the
requested target-side test actually runs.
