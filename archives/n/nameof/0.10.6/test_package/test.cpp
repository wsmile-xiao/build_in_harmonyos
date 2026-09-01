// Consumer test for nameof 0.10.6 (header-only).
// Exercises the real public API: NAMEOF / NAMEOF_TYPE / NAMEOF_ENUM and
// nameof::nameof_type<>. Returns non-zero on any failed assertion.
#include <nameof.hpp>

#include <cstdio>
#include <string>

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond)                                                          \
  do {                                                                       \
    ++g_checks;                                                              \
    if (!(cond)) {                                                           \
      ++g_failed;                                                            \
      std::printf("FAIL: %s\n", #cond);                                      \
    }                                                                        \
  } while (0)

enum class Color { RED, GREEN, BLUE };

int some_function() { return 42; }

int main() {
    int counter = 0;
    (void)counter;

    // NAMEOF: variable name
    CHECK(NAMEOF(counter) == "counter");

    // NAMEOF_TYPE: type name
    CHECK(NAMEOF_TYPE(int) == "int");
    CHECK(NAMEOF_SHORT_TYPE(std::string) == "string");

    // NAMEOF_ENUM: enum value name
    CHECK(NAMEOF_ENUM(Color::RED) == "RED");
    CHECK(NAMEOF_ENUM(Color::GREEN) == "GREEN");

    // NAMEOF of a function
    CHECK(NAMEOF(some_function) == "some_function");

    // nameof::nameof_type<>: compile-time type name
    CHECK(nameof::nameof_type<double>() == "double");

    std::printf("nameof test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
