// test_package consumer for the mikelankamp-fpm Conan package (R34).
//
// The consumer uses only the *installed* headers from the Conan package (the
// upstream source tree is not on the include path) and checks observable
// results instead of printing. It is the package's "HarmonyOS specific test"
// row: every check below runs on the OHOS aarch64 device.
//
//   1  integer construction + exact integer arithmetic
//   2  exact fractional arithmetic (1.5 + 2.25 == 3.75, no drift)
//   3  raw underlying representation round trip (1.5 == 98304 / 65536)
//   4  cross-format conversion fixed_16_16 -> fixed_24_8 -> fixed_8_24
//   5  fpm::sqrt(2) matches the double reference within 1e-4
//   6  fpm::sin/cos/atan sanity against the double reference
//   7  fpm::ceil/floor/round/fmod behave like their <cmath> counterparts
//   8  operator<< produces a number std::strtod parses back to the same value
//   9  operator>> parses "1.5" back to the exact fixed-point value
//  10  std::hash<fpm::fixed> is stable and injective on a sample set
#include <fpm/fixed.hpp>
#include <fpm/ios.hpp>
#include <fpm/math.hpp>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <sstream>
#include <string>

namespace {

int failures = 0;

void check(bool ok, const char* what)
{
    if (!ok)
    {
        std::printf("FAIL: %s\n", what);
        ++failures;
    }
}

bool near(double actual, double expected, double tol)
{
    return std::fabs(actual - expected) <= tol;
}

}  // namespace

int main()
{
    using f16 = fpm::fixed_16_16;
    using f24 = fpm::fixed_24_8;
    using f8 = fpm::fixed_8_24;

    // 1. integer construction + exact integer arithmetic ------------------
    check(f16{3} + f16{4} == f16{7}, "3 + 4 == 7");
    check(f16{9} * f16{9} == f16{81}, "9 * 9 == 81");
    check(-f16{5} == f16{-5}, "unary minus");

    // 2. exact fractional arithmetic -------------------------------------
    check(f16{1.5} + f16{2.25} == f16{3.75}, "1.5 + 2.25 == 3.75");
    check(f16{0.1} + f16{0.2} == f16{0.3}, "0.1 + 0.2 == 0.3 (fixed-point exact)");
    check(static_cast<double>(f16{3.75}) == 3.75, "explicit double cast is lossless");

    // 3. raw representation round trip ------------------------------------
    check(f16::from_raw_value(98304).raw_value() == 98304, "from_raw_value keeps 98304");
    check(static_cast<double>(f16::from_raw_value(98304)) == 1.5,
          "raw 98304 == 1.5 for fixed_16_16");

    // 4. cross-format conversion ------------------------------------------
    check(static_cast<f24>(f16{2.5}) == f24{2.5}, "fixed_16_16 -> fixed_24_8");
    check(static_cast<f8>(f16{-1.25}) == f8{-1.25}, "fixed_16_16 -> fixed_8_24");
    check(static_cast<double>(static_cast<f8>(f24{4.5})) == 4.5,
          "fixed_24_8 -> fixed_8_24 -> double");

    // 5. fpm::sqrt against the double reference ---------------------------
    check(near(static_cast<double>(fpm::sqrt(f16{2})), std::sqrt(2.0), 1e-4),
          "sqrt(2) within 1e-4 of the double reference");
    check(fpm::sqrt(f16{9}) == f16{3}, "sqrt(9) == 3 exactly");

    // 6. trigonometry sanity ----------------------------------------------
    // Tolerance is one LSB of fixed_16_16 (1/65536 = 1.52587890625e-5): the
    // upstream minimax polynomials return 65535/65536 (i.e. 1 LSB low) for
    // both sin(pi/2) and cos(0). That is upstream approximation behaviour in
    // the unmodified v1.1.0 headers, not an OHOS deviation.
    constexpr double one_LSB = 1.0 / 65536.0;
    check(near(static_cast<double>(fpm::sin(f16::half_pi())), 1.0, one_LSB),
          "sin(pi/2) == 1 within 1 LSB");
    check(near(static_cast<double>(fpm::cos(f16{0})), 1.0, one_LSB),
          "cos(0) == 1 within 1 LSB");
    check(near(static_cast<double>(fpm::atan(f16{1})), 0.7853981634, 1e-4),
          "atan(1) == pi/4 within 1e-4");

    // 7. rounding family / fmod -------------------------------------------
    check(fpm::ceil(f16{1.25}) == f16{2}, "ceil(1.25) == 2");
    check(fpm::floor(f16{1.75}) == f16{1}, "floor(1.75) == 1");
    check(fpm::round(f16{1.5}) == f16{2}, "round(1.5) == 2 (away from zero)");
    check(fpm::fmod(f16{5.5}, f16{2}) == f16{1.5}, "fmod(5.5, 2) == 1.5");

    // 8. operator<< produces a parseable decimal --------------------------
    {
        std::ostringstream oss;
        oss << f16{3.75};
        const std::string text = oss.str();
        check(!text.empty(), "operator<< produced output");
        check(near(std::strtod(text.c_str(), nullptr), 3.75, 1e-9),
              "operator<< output parses back to 3.75");
    }

    // 9. operator>> parses text back to the exact value -------------------
    {
        std::istringstream iss("1.5");
        f16 parsed{};
        iss >> parsed;
        check(!iss.fail(), "operator>> succeeded on \"1.5\"");
        check(parsed == f16{1.5}, "operator>> yields exactly 1.5");
    }

    // 10. std::hash behaviour ---------------------------------------------
    {
        const std::hash<f16> hasher{};
        check(hasher(f16{1.5}) == hasher(f16{1.5}), "std::hash is stable");
        check(hasher(f16{1.5}) != hasher(f16{2.5}),
              "std::hash differs for different values");
    }

    if (failures != 0)
    {
        std::printf("mikelankamp-fpm consumer FAILED: %d check(s)\n", failures);
        return 1;
    }

    std::printf("mikelankamp-fpm consumer OK: 26 checks passed "
                "(arithmetic raw conversion sqrt trig rounding io hash)\n");
    return 0;
}
