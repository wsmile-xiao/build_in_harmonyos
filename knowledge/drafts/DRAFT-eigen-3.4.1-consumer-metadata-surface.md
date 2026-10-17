# Draft: eigen consumer metadata surface for header-only packages

> Source event: eigen/3.4.1 OHOS shadow CI on 2026-08-28.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Header-only packages can compile even when their consumer metadata is wrong. In
the eigen run, the real validation boundary is the installed include tree plus
the generated consumer files, not the absence of `bin/` or `lib/`.

## Recommended handling

1. Record the installed include surface explicitly.
2. Record generated CMake and pkg-config metadata explicitly.
3. Build the consumer through Conan `CMakeDeps` and `CMakeToolchain`, not from
   the source checkout.
4. Keep the metadata evidence next to the consumer runtime result.

## Evidence from eigen

The passing shadow run installed:

```text
include/eigen3/Eigen
include/eigen3/unsupported
share/eigen3/cmake
share/pkgconfig/eigen3.pc
```

The consumer test then built `test_eigen` through Conan metadata and executed
successfully with:

```text
eigen smoke test: PASS (matmul + norm OK)
```

## Classification guidance

For Eigen-like header-only packages, include-tree evidence and generated
consumer metadata should be treated as a first-class success signal. A build
that only reports `no artifacts found` is incomplete until the metadata surface
is documented.

## Boundaries

This draft does not claim full upstream Eigen coverage. It only records the
package surface needed by the consumer build path.
