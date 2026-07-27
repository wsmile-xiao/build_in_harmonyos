# Qhull

Qhull computes convex hulls, Delaunay triangulations, Voronoi diagrams,
halfspace intersections, and related geometric structures.

## HarmonyOS PC adaptation

- Builds the reentrant shared C library, `libqhull_r`.
- Uses the official CMake build and compiles the upstream CTest targets.
- Links only the platform math library; there are no third-party Conan dependencies.
- Packages library headers and the shared library, without the upstream command-line tools.

## Verification

The Conan consumer test calls `qh_new_qhull` on a two-dimensional square and
checks the resulting vertex and facet counts. Cross builds compile and link the
test but do not execute it without a compatible HarmonyOS target.

## References

- https://github.com/qhull/qhull
- http://www.qhull.org
