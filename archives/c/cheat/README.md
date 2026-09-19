# cheat

A tiny and portable C11 unit testing framework that requires no installation
or configuration — only a header file (`cheat.h`) and a test case using the
`CHEAT_TEST` / `cheat_assert` macros. Companion headers `cheats.h`
(specialized assertions) and `windowed.h` (Windows prototypes) extend it.

## OpenHarmony adaptation

The package installs the upstream headers at the include/ root (`cheat.h`,
`cheats.h`, `windowed.h`) and exports the CMake target `cheat::cheat`. It is a
pure header-library with zero runtime dependencies (only the C standard
library), so no compilation occurs during `conan create`; the recipe's
`build()` compiles and executes the upstream `tests/*.c` suite (25 independent
test files) with the OHOS clang toolchain as the upstream-test gate, and the
consumer `test_package` builds two programs — `test_cheat` (3 CHEAT_TEST
assertion cases) and `test_ohos` (3 OHOS-specific platform/POSIX cases) —
that run against the packaged headers.

Adaptation notes: `tests/jammed.c` and `tests/slow.c` need
`-D_POSIX_C_SOURCE=200112L` on OHOS (clang does not predefine the POSIX level,
so they would fall into the static-`sleep` branch that conflicts with
`unistd.h`); the flag is applied in the recipe's upstream-test gate only and
does not alter any test semantics.

## Consumer usage

```cmake
find_package(cheat CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE cheat::cheat)
```

```c
#include <cheat.h>

CHEAT_TEST(mathematics_still_work,
    cheat_assert(2 + 2 == 4);
    cheat_assert_not(2 + 2 == 5);
)
```

## Versions

| Version | Status | Date |
|---------|--------|------|
| 1.0.4   | built  | 2026-09-19 |
