#include <cmath>
#include <iostream>

#include <gcem.hpp>

constexpr int kFactorial = gcem::factorial(5);
constexpr int kGcd = gcem::gcd(84, 30);
constexpr int kLcm = gcem::lcm(6, 8);
constexpr double kSqrt = gcem::sqrt(81.0);
constexpr double kPow = gcem::pow(2.0, 8.0);
constexpr long double kLog = gcem::log(0.1L);
constexpr long double kIncompleteBeta =
    gcem::incomplete_beta(0.9L, 0.9L, 0.1L);

static_assert(kFactorial == 120, "gcem::factorial constexpr evaluation failed");
static_assert(kGcd == 6, "gcem::gcd constexpr evaluation failed");
static_assert(kLcm == 24, "gcem::lcm constexpr evaluation failed");
static_assert(kSqrt == 9.0, "gcem::sqrt constexpr evaluation failed");
static_assert(kPow > 255.999 && kPow < 256.001,
              "gcem::pow constexpr evaluation failed");
static_assert(kLog < -2.30258L && kLog > -2.30259L,
              "gcem::log long double constexpr evaluation failed");
static_assert(kIncompleteBeta > 0.11464L && kIncompleteBeta < 0.11465L,
              "gcem::incomplete_beta long double constexpr evaluation failed");

int main() {
    int failures = 0;
    const auto check = [&failures](const char* name, bool condition) {
        if (!condition) {
            std::cerr << "FAIL: " << name << std::endl;
            ++failures;
        }
    };

    check("factorial", kFactorial == 120);
    check("gcd", kGcd == 6);
    check("lcm", kLcm == 24);
    check("sqrt", std::fabs(gcem::sqrt(81.0) - 9.0) < 1e-12);
    check("pow", std::fabs(gcem::pow(2.0, 8.0) - 256.0) < 1e-12);
    check("sin", std::fabs(gcem::sin(0.5) - std::sin(0.5)) < 1e-12);
    check("erf", std::fabs(gcem::erf(0.5) - std::erf(0.5)) < 1e-12);
    check("log long double",
          std::fabs(static_cast<double>(gcem::log(0.1L) +
                                        2.302585092994045684L)) < 1e-12);
    check("incomplete_beta long double",
          std::fabs(static_cast<double>(gcem::incomplete_beta(0.9L, 0.9L, 0.1L) -
                                        0.11464699677582491921L)) < 1e-12);

    if (failures == 0) {
        std::cout << "gcem consumer checks passed: 16" << std::endl;
    }
    return failures == 0 ? 0 : 1;
}
