# Draft: eigen consumer negative test must remove the packaged include path

> Source event: eigen/3.4.1 OHOS shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

A consumer test can pass for the wrong reason if the source tree or host system
headers are still visible. For eigen, the smoke test is only meaningful if a
destructive negative probe proves the packaged include path is actually needed.

## Recommended handling

1. Keep a positive consumer smoke test for `<Eigen/Dense>`.
2. Add a destructive negative probe that removes the packaged include path.
3. Treat the negative probe as the boundary that proves the test is not a
   source-tree accidental success.
4. Record the negative result in the PR description so reviewers can see the
   dependency boundary.

## Evidence from eigen

The shadow run passed the positive smoke test:

```text
eigen smoke test: PASS (matmul + norm OK)
```

The same run then removed the packaged include path and confirmed the consumer
test failed as expected. That closes the false-green case where the build might
be using headers from somewhere other than the installed package.

## Classification guidance

For header-only packages, the negative include-path test is the simplest proof
that the consumer test depends on the package surface rather than a stray host
include path.

## Boundaries

This draft does not claim to validate every Eigen module. It only proves the
packaged include path is required for the tested dense consumer path.
