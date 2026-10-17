# Draft: eigen unsupported ThreadPool pthread_cancel boundary

> Source event: `eigen/3.4.1` OHOS pre-scan and shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

The source pre-scan found `pthread_cancel` in:

```text
unsupported/Eigen/CXX11/src/ThreadPool/ThreadCancel.h
```

The relevant upstream code only enables thread cancellation when
`EIGEN_OS_GNULINUX` is true:

```text
#if EIGEN_OS_GNULINUX
  #define EIGEN_THREAD_CANCEL(t) pthread_cancel(t.native_handle());
  #define EIGEN_SUPPORTS_THREAD_CANCELLATION 1
#else
  #define EIGEN_THREAD_CANCEL(t)
#endif
```

The final eigen test package does not exercise unsupported ThreadPool. It
validates the core `<Eigen/Dense>` consumer path: matrix multiplication and
`Vector3d::norm()` on the OHOS device.

## Recommended handling

For Eigen packages on OHOS:

1. Keep `pthread_cancel` as a known pre-scan risk tied to `unsupported/`.
2. Do not patch core Eigen just because the token appears in the source tree.
3. Do not claim unsupported Tensor/ThreadPool runtime support from a Dense-only
   smoke test.
4. If a downstream package uses `unsupported/Eigen/CXX11/ThreadPool`, add a
   targeted compile probe and, where thread lifecycle matters, a target runtime
   test for the exact downstream usage.
5. If OHOS macro detection ever makes `EIGEN_OS_GNULINUX` true, handle it with
   a narrow guard or feature test rather than a no-op `pthread_cancel` stub.

## Evidence from eigen

- Pre-scan found `pthread_cancel` in the unsupported ThreadPool header.
- No patch was applied to Eigen sources.
- Shadow CI r2 passed the packaged `<Eigen/Dense>` consumer test.
- The test output was: `eigen smoke test: PASS (matmul + norm OK)`.

## Relation to existing knowledge

Existing entries cover the general HarmonyOS/pthread cancellation API gap. This
draft records the Eigen-specific boundary: the package installs
`unsupported/`, but the accepted smoke path only covers core Dense headers. That
distinction prevents a false compatibility claim for downstreams that depend on
Eigen's unsupported CXX11 ThreadPool or Tensor stack.

## Boundaries

This draft is not evidence that unsupported ThreadPool fails on OHOS. It is a
scope marker: it says which part of the installed header tree was not validated
by the current `eigen/3.4.1` test package.
