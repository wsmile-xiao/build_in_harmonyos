# matchit

Header-only C++17 pattern-matching library (matchit.cpp by Bowen Fu) — value
matching with `match`, `some`, `as`, `ds`, `ooo`, `app`, extractor, guards,
ranges and friends; heavily inspired by Rust pattern matching.

## OpenHarmony adaptation

The package installs the upstream single header `include/matchit.h` and exports
the CMake target `matchit::matchit`. It is a pure header-library with zero
runtime dependencies, so no compilation occurs during `conan create`; the
consumer `test_package` compiles a program exercising the real matchit API
(literal / wildcard / some / as / ds / ooo) to validate the package on the
OHOS aarch64 toolchain.

Upstream test suite: 78 gtest cases across 7 suites (app/constexpr/ds/expr/
id/legacy/noRet), all pass on the OHOS clang-15 toolchain (gtest 1.17.0
consumed from the ohpcd registry since GitHub direct fetch of googletest is
unavailable on the worker).

## Consumer usage

```cmake
find_package(matchit CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE matchit::matchit)
```

```cpp
#include <matchit.h>
#include <memory>
using namespace matchit;

struct Base   { virtual ~Base() = default; };
struct Derived : Base {};

int classify(int x) {
  return match(x)(
      pattern | 0 = expr(0),
      pattern | 1 = expr(1),
      pattern | _ = expr(-1));
}

auto const p = std::make_unique<Base>(new Derived{});
bool is_derived = matched(p, some(as<Derived>(_)));  // true
```

## Versions

| Version | Status | Build date |
| --- | --- | --- |
| [1.0.0](./1.0.0/) | built | 2026-09-02 |

## References

- Upstream: https://github.com/BowenFu/matchit.cpp
- License: MIT