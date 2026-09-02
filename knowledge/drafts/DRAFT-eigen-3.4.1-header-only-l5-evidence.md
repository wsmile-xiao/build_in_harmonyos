# Draft: eigen header-only L5 evidence standard

> Source event: `eigen/3.4.1` OHOS shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Header-only packages can make binary-oriented CI gates look weak. In the eigen
shadow run, L2 skipped because there is no `bin/` directory and L5 warned that
no binary artifacts were found:

```text
L2_RESULT=skip: no bin/ dir
L5_RESULT=warn: no artifacts found
```

That is expected for `eigen`, but it must not be treated as automatic success.
The package still needs proof that the installed headers and generated consumer
metadata are real and usable on the target.

## Recommended handling

For eigen-like header-only C++ packages:

1. Verify the installed include tree, not just the absence of libraries.
2. Record the generated consumer metadata, such as CMake package files and
   pkg-config files when upstream installs them.
3. Build a consumer `test_package` through Conan `CMakeDeps`/`CMakeToolchain`
   so include paths and targets come from the package, not from a local source
   checkout.
4. Run the consumer on the OHOS device when policy permits executable launch.
5. Add or preserve a destructive negative check that proves the consumer test
   really depends on the packaged headers.

## Evidence from eigen

The passing shadow run installed:

```text
include/eigen3/Eigen
include/eigen3/unsupported
share/eigen3/cmake
share/pkgconfig/eigen3.pc
```

The consumer test included `<Eigen/Dense>`, built `test_eigen`, and executed on
the device with:

```text
eigen smoke test: PASS (matmul + norm OK)
```

The L1e destructive negative test then removed the packaged include path and
confirmed that the same consumer test fails. That closes the common false-green
case where the test accidentally uses headers from the source tree or host
environment.

## Classification guidance

`L5_RESULT=warn` is acceptable for eigen only because all of the following are
true:

- the package is intentionally header-only;
- expected include and metadata directories exist;
- the consumer test builds through Conan metadata;
- the target-side runtime test passes;
- the destructive negative test proves package dependency.

If any item is missing, keep L5 as an unresolved warning instead of claiming
the package is fully validated.

## Boundaries

This draft does not claim that every `unsupported/` Eigen module works on
HarmonyOS. It only covers the packaged header tree and the tested dense linear
algebra consumer path.
