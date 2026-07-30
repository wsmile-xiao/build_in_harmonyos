# CLHEP

CLHEP is a collection of C++ utility classes used by high-energy physics
software, including random-number engines, geometry vectors, and physical
constants.

## OpenHarmony adaptation

The package is built with CMake and exports the upstream CMake target
`CLHEP::CLHEP`. Upstream CTest tests are enabled and run whenever the target
binary can execute on the build machine.

## Consumer usage

```cmake
find_package(CLHEP CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE CLHEP::CLHEP)
```

## Versions

| Version | Status |
| --- | --- |
| [2.4.7.1](./2.4.7.1/) | pending validation |

## References

- Upstream: https://proj-clhep.web.cern.ch/proj-clhep/
- License: BSD-3-Clause
