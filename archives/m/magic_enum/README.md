# magic_enum

Header-only C++17 library that provides static reflection for enums — work
with any enum type without any macro or boilerplate code.

## OpenHarmony adaptation

The package installs the upstream `magic_enum/*.hpp` headers (9 files under
`include/magic_enum/`) and exports the CMake target `magic_enum::magic_enum`.
It is a pure header-library with zero runtime dependencies, so no compilation
occurs during `conan create`; the consumer `test_package` compiles a program
that exercises the real `magic_enum` API to validate the package.

## Consumer usage

```cmake
find_package(magic_enum CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE magic_enum::magic_enum)
```

```cpp
#include <magic_enum.hpp>

enum class Color { RED, GREEN, BLUE };

auto name = magic_enum::enum_name(Color::GREEN);   // "GREEN"
auto value = magic_enum::enum_cast<Color>("RED");  // Color::RED
```

## Versions

| Version | Status | Build date |
| --- | --- | --- |
| [0.9.8](./0.9.8/) | built | 2026-08-24 |

## References

- Upstream: https://github.com/Neargye/magic_enum
- License: MIT
