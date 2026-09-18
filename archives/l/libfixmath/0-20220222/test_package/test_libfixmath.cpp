#include <cstdio>
#include <cstring>

#include <libfixmath/fix16.h>
#include <libfixmath/fix16.hpp>

namespace {

int failures = 0;

void expect_equal(const char *name, fix16_t actual, fix16_t expected)
{
    if (actual != expected) {
        std::fprintf(stderr, "%s: got %d, expected %d\n", name,
                     static_cast<int>(actual), static_cast<int>(expected));
        ++failures;
    }
}

void expect_true(const char *name, bool condition)
{
    if (!condition) {
        std::fprintf(stderr, "%s: condition failed\n", name);
        ++failures;
    }
}

}  // namespace

int main()
{
    const Fix16 one_and_half(1.5);
    const Fix16 two(static_cast<int16_t>(2));

    expect_equal("C++ addition", (one_and_half + two).value, F16(3.5));
    expect_equal("C++ multiplication", (one_and_half * two).value, F16(3.0));
    expect_equal("C++ division", (one_and_half / two).value, F16(0.75));
    expect_equal("C++ square root", Fix16(static_cast<int16_t>(4)).sqrt().value, F16(2.0));

    expect_equal("C addition", fix16_add(F16(1.25), F16(2.5)), F16(3.75));
    expect_equal("C subtraction", fix16_sub(F16(1.25), F16(2.5)), F16(-1.25));
    expect_equal("C multiplication", fix16_mul(F16(-2.0), F16(1.5)), F16(-3.0));
    expect_equal("C division", fix16_div(F16(3.0), F16(4.0)), F16(0.75));
    expect_equal("C square root", fix16_sqrt(F16(9.0)), F16(3.0));
    expect_equal("C exponent", fix16_exp(0), fix16_one);
    expect_equal("C interpolation", fix16_lerp16(0, F16(2.0), 32768), fix16_one);
    expect_equal("C cosine", fix16_cos(0), fix16_one);

    char buffer[24] = {};
    fix16_to_str(F16(-12.5), buffer, 4);
    expect_true("string rendering", std::strcmp(buffer, "-12.5000") == 0);
    expect_equal("string parsing", fix16_from_str(buffer), F16(-12.5));
    expect_true("C++ conversion", static_cast<double>(one_and_half) == 1.5);
    expect_true("comparison operator", two > one_and_half);

    if (failures != 0) {
        return 1;
    }

    std::puts("libfixmath C/C++ consumer API: PASS");
    return 0;
}
