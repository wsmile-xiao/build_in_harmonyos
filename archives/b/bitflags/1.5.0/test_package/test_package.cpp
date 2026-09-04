// test_package.cpp — Substantive consumer test for bitflags 1.5.0
// Verifies that the packaged bitflags/bitflags.hpp header can be consumed from
// a downstream C++ project and that flag declaration, auto-generated values,
// and bitwise ops produce correct results. This is a downstream-consumer test
// (Conan L1), not the full upstream gtest suite.

#include <bitflags/bitflags.hpp>

#include <cstdio>
#include <cstdlib>

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

// Declare a flags set exactly as documented in the upstream README.
BEGIN_BITFLAGS(Flags)
FLAG(none)
FLAG(flag_a)
FLAG(flag_b)
FLAG(flag_c)
END_BITFLAGS(Flags)

int main()
{
    // Auto-generated distinct flag values
    TEST("auto-generated flag values");
    bool distinct = Flags::none.bits != Flags::flag_a.bits
                 && Flags::flag_a.bits != Flags::flag_b.bits
                 && Flags::flag_b.bits != Flags::flag_c.bits;
    ASSERT_TRUE(distinct);

    // OR-combine flags
    TEST("operator|");
    Flags f = Flags::flag_a | Flags::flag_b;
    ASSERT_TRUE(static_cast<bool>(f & Flags::flag_a));
    ASSERT_TRUE(static_cast<bool>(f & Flags::flag_b));
    ASSERT_TRUE(!static_cast<bool>(f & Flags::flag_c));

    // AND checks membership
    TEST("operator&");
    ASSERT_TRUE(static_cast<bool>(f & Flags::flag_a));

    // XOR toggles membership
    TEST("operator^");
    Flags x = f ^ Flags::flag_a;
    ASSERT_TRUE(!static_cast<bool>(x & Flags::flag_a));
    ASSERT_TRUE(static_cast<bool>(x & Flags::flag_b));

    // NOT inverts the whole set
    TEST("operator~");
    Flags n = ~Flags::none;
    ASSERT_TRUE(static_cast<bool>(n & Flags::flag_a));

    // empty / all helpers
    TEST("empty / all");
    Flags empty_flags = Flags::empty();
    ASSERT_TRUE(empty_flags.is_empty());
    Flags all_flags = Flags::all();
    ASSERT_TRUE(all_flags.is_all());

    if (failures == 0) {
        std::printf("PASS: all bitflags consumer checks passed\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL: %d bitflags consumer check(s) failed\n", failures);
    return 1;
}