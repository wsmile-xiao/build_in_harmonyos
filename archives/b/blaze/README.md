# Blaze

Blaze is a high-performance C++ math library for dense and sparse arithmetic.
It is a header-only library and requires C++14 or newer.

## OpenHarmony adaptation

The package installs the upstream `blaze/` headers and exports the CMake target
`Blaze::Blaze`. The recipe runs an upstream DynamicVector class test with the
profile-provided C++ compiler before packaging.

## Consumer usage

```cmake
find_package(Blaze CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE Blaze::Blaze)
```

## Versions

| Version | Status | Build date |
| --- | --- | --- |
| [3.8.2](./3.8.2/) | built | 2026-07-28 |

## References

- Upstream: https://bitbucket.org/blaze-lib/blaze
- License: BSD-3-Clause
