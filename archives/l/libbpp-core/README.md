# libbpp-core

## Intro
Bio++ Core Library: C++ classes for bioinformatics and numerical calculus (ranges, vectors, optimization, distributions, graphs).

## OHOS adaptation
- Build system: cmake
- No external dependencies; upstream builds static + shared targets
- Upstream test suite: 19 ctest cases under test/, enabled with BUILD_TESTING=ON
- Consumer test covers Bpp/Numeric/Range.h real API

## Dependencies
- None

## Verification
- Upstream `ctest --output-on-failure` in build folder
- Consumer `./test_probe` linked against packaged bpp-core

## References
- https://github.com/BioPP/bpp-core
- https://github.com/BioPP/bpp-core/archive/refs/tags/v2.4.1.tar.gz
