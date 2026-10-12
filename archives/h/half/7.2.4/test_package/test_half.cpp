// Layer-2 consumer test for the `half` package (ROCm 7.2.4).
//
// Real API exercise: include the installed header <half/half.hpp>, construct
// half values from float/double, round-trip them back and verify numerical
// correctness plus edge values.  Every check is enforced by require(), which
// aborts the process on failure -- deliberately NOT assert(), because Conan's
// Release build defines NDEBUG (which would silently disable assert()).
//
// NOTE: half.hpp exposes no version macro; its version ("Version 1.12.0")
// lives in the header comment only.  The *package* version is the ROCm release
// train 7.2.4 (see notes.md).  The HALF_HALF_HPP include guard is used below to
// prove the header was really pulled in from the package.

#include <half/half.hpp>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <vector>

using half_float::half;
using half_float::half_cast;

static std::uint64_t g_checks = 0;

static void require(bool condition, const char *what)
{
    if (!condition)
    {
        std::fprintf(stderr, "test_half: FAILED check: %s\n", what);
        std::abort();
    }
    ++g_checks;
}

int main()
{
#ifndef HALF_HALF_HPP
#error "half/half.hpp was not included from the package (include guard missing)"
#endif
    require(sizeof(half) == 2, "sizeof(half) == 2");

    // -- exact construction / conversion -------------------------------
    require((float)half(1.0f) == 1.0f, "half(1.0f) == 1.0f");
    require((float)half(-1.0f) == -1.0f, "half(-1.0f) == -1.0f");
    require((float)half(0.0f) == 0.0f, "half(0.0f) == 0.0f");
    require((float)half(0.5f) == 0.5f, "half(0.5f) == 0.5f");
    require((float)half(0.25f) == 0.25f, "half(0.25f) == 0.25f");
    require((float)half(2.0f) == 2.0f, "half(2.0f) == 2.0f");
    require((float)half(-3.5f) == -3.5f, "half(-3.5f) == -3.5f");
    require((float)half(1.5f) == 1.5f, "half(1.5f) == 1.5f");
    require((float)half(3.0f) == 3.0f, "half(3.0f) == 3.0f");
    require((double)half(0.5f) == 0.5, "double(half(0.5f)) == 0.5");

    // -- operators ------------------------------------------------------
    require(half(1.0f) == half(1.0f), "half == half");
    require(half(1.0f) != half(2.0f), "half != half");
    require(half(1.0f) < half(2.0f), "half < half");
    require(half(2.0f) > half(1.0f), "half > half");
    require((float)(half(1.5f) + half(2.5f)) == 4.0f, "half + half");
    require((float)(half(4.0f) - half(1.0f)) == 3.0f, "half - half");
    require((float)(half(2.0f) * half(3.0f)) == 6.0f, "half * half");
    require((float)(half(6.0f) / half(2.0f)) == 3.0f, "half / half");

    // -- round-trip conversion (float -> half -> float) -----------------
    const float exact[] = {1.0f, 0.5f, 0.25f, -2.0f, 1.5f, 0.0f, -0.125f};
    for (std::size_t i = 0; i < sizeof(exact) / sizeof(exact[0]); ++i)
        require((float)half(exact[i]) == exact[i], "float->half->float round-trip");

    // -- numeric_limits -------------------------------------------------
    require(std::numeric_limits<half>::is_specialized, "numeric_limits specialized");
    require(std::numeric_limits<half>::digits == 11, "numeric_limits::digits == 11");
    require((float)std::numeric_limits<half>::max() == 65504.0f, "half max == 65504");
    require((float)std::numeric_limits<half>::denorm_min() > 0.0f, "denorm_min > 0");
    require(std::isinf((float)std::numeric_limits<half>::infinity()),
            "numeric_limits<half>::infinity() is inf");
    require(std::isnan((float)std::numeric_limits<half>::quiet_NaN()),
            "numeric_limits<half>::quiet_NaN() is NaN");

    // -- edge values ----------------------------------------------------
    require(std::isinf((float)half(1.0e9f)), "overflow 1e9f -> +inf");
    require(std::isinf((float)half(-1.0e9f)), "overflow -1e9f -> -inf");
    require(std::signbit((float)half(-2.0f)), "signbit(half(-2.0f))");
    require(!std::signbit((float)half(2.0f)), "!signbit(half(2.0f))");
    require((float)half(0.1f) != 0.1f, "0.1f is not exactly representable");
    require(std::fabs((float)half(0.1f) - 0.1f) < 5.0e-4f, "half(0.1f) rounds close");

    // -- half_cast ------------------------------------------------------
    require(half_cast<float>(half(1.5f)) == 1.5f, "half_cast<float>");
    require(half_cast<int, std::round_to_nearest>(half(3.0f)) == 3,
            "half_cast<int,round_to_nearest>");
    require(std::fabs((float)half_cast<half, std::round_to_nearest>(3.14159f) - 3.14159f)
                < 1.0e-3f, "half_cast<half,round_to_nearest>(pi)");

    std::printf("test_half: %llu checks passed\n",
                (unsigned long long)g_checks);
    if (g_checks < 40)
    {
        std::fprintf(stderr, "test_half: expected at least 40 checks, ran %llu\n",
                     (unsigned long long)g_checks);
        return 2;
    }
    return 0;
}
