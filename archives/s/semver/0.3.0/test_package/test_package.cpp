// test_package.cpp — Substantive consumer test for semver 0.3.0
// Verifies that the packaged semver.hpp can be consumed from a downstream
// C++ project and that core parse / compare / satisfy operations produce
// correct results. This is a downstream-consumer test (Conan L1), not the
// full upstream suite.

#include <semver.hpp>

#include <cstdio>
#include <cstdlib>
#include <string>

static int failures = 0;
static const char *last_test = "";

#define TEST(name) do { last_test = name; } while (0)

#define ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        std::fprintf(stderr, "FAIL [%s] line %d: condition false\n", \
                     last_test, __LINE__); \
        failures++; \
    } \
} while (0)

int main()
{
    // Parse from string (semver::version constructor from string_view)
    TEST("parse from string");
    const semver::version v1{"1.2.3"};
    ASSERT_TRUE(v1.major == 1);
    ASSERT_TRUE(v1.minor == 2);
    ASSERT_TRUE(v1.patch == 3);

    // Round-trip to_string
    TEST("to_string round-trip");
    ASSERT_TRUE(semver::to_string(v1) == "1.2.3");

    // Comparison operators
    TEST("comparison");
    const semver::version v2{"1.2.4"};
    const semver::version v3{"1.2.3"};
    ASSERT_TRUE(v1 < v2);
    ASSERT_TRUE(v1 == v3);

    // Range satisfies (semver 2.0.0 range syntax)
    // NOTE: satisfies() lives in semver::range namespace in v0.3.0;
    // v0.3.0 lexer supports only <,>,<=,>=,= and || (no ^ / ~ caret syntax).
    TEST("satisfies range");
    ASSERT_TRUE(semver::range::satisfies(v1, ">=1.0.0 <2.0.0"));
    ASSERT_TRUE(semver::range::satisfies(v1, "1.2.3"));
    ASSERT_TRUE(!semver::range::satisfies(v1, ">=2.0.0"));

    // Header version macros
    TEST("version macro");
    ASSERT_TRUE(SEMVER_VERSION_MAJOR == 0);
    ASSERT_TRUE(SEMVER_VERSION_MINOR == 3);
    ASSERT_TRUE(SEMVER_VERSION_PATCH == 0);

    if (failures == 0) {
        std::printf("PASS: all semver consumer checks passed\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL: %d semver consumer check(s) failed\n", failures);
    return 1;
}
