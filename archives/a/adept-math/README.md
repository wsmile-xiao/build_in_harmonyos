# adept-math

Adept is a C++ library for automatic differentiation, arrays, and numerical
optimization.

This package builds the Adept 2.1.3 GitHub snapshot as a static library for
HarmonyOS PC. The formal upstream release tarballs stop at 2.1.1; the 2.1.3
task version is provided as the upstream GitHub tag `v2.1.3`.

## Conan

```cmake
find_package(adept-math CONFIG REQUIRED)
target_link_libraries(app PRIVATE adept-math::adept-math)
```

The packaged library is built without optional BLAS/LAPACK acceleration. Core
automatic differentiation, array, and optimizer APIs remain available; matrix
multiplication and LAPACK-backed linear algebra report unavailable through the
upstream Adept feature checks.

## References

- https://www.met.reading.ac.uk/clouds/adept/
- https://github.com/rjhogan/Adept-2
