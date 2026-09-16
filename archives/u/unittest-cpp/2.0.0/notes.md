# unittest-cpp 2.0.0

- Upstream: https://github.com/unittest-cpp/unittest-cpp/tree/v2.0.0
- Build system: CMake.
- External Conan requirements: none identified in the upstream build files.
- The recipe runs the upstream `TestUnitTest++` executable after building.
- Archive SHA256 verified: `74852198877dc2fdebdc4e5e9bd074018bf8ee03a13de139bfe41f4585b2f5b9` (54100 bytes, GitHub tag archive).
- One portability patch `patches/0001-cmake-min-version.patch`: bumps `cmake_minimum_required(VERSION 2.8.1)` to `3.5` (CMake >= 3.27 dropped <3.5 compatibility, configure failed otherwise).
- CMakeDeps generates `unittest-cpp` config (upstream project name `UnitTest++` is not a valid Conan package name); the recipe registers a `UnitTest++` target alias so downstream `target_link_libraries(UnitTest++)` keeps working.
