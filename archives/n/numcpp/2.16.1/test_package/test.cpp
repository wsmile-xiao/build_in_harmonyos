// Consumer test for numcpp 2.16.1 (header-only) on HarmonyOS PC (ohos-aarch64).
// Compiles the full NumCpp.hpp umbrella (which parses every module header:
// Special/DateTime/Logging/Polynomial/Random/... under default Boost-enabled
// settings) and then verifies representative numeric behaviour end to end.
#include "NumCpp.hpp"

#include <cmath>
#include <complex>
#include <cstddef>
#include <iostream>
#include <string>

static int failures = 0;
static int assertions = 0;

#define CHECK_MSG(cond, msg)                                                  \
    do {                                                                      \
        ++assertions;                                                         \
        if (!(cond)) {                                                        \
            std::cerr << "FAIL: " << msg << "  [" #cond " @ line "            \
                      << __LINE__ << "]" << std::endl;                        \
            ++failures;                                                       \
        }                                                                     \
    } while (0)

#define CHECK_EQ(a, b) CHECK_MSG((a) == (b), "eq")
#define CHECK_NEAR(a, b, tol) CHECK_MSG(std::abs((a) - (b)) <= (tol), "near")

int main()
{
    // ── NdArray construction / arithmetic / reductions ──
    nc::NdArray<int> a = { {1, 2, 3}, {4, 5, 6} };
    CHECK_EQ(a.shape().rows, 2);
    CHECK_EQ(a.shape().cols, 3);
    CHECK_EQ(nc::sum(a).item(), 21);
    nc::NdArray<int> b = a * 2;
    CHECK_EQ(b(1, 2), 12);
    nc::NdArray<int> c = a + b;
    CHECK_EQ(nc::sum(c).item(), 63);

    // ── arange / reshape / transpose ──
    nc::NdArray<int> r = nc::arange<int>(0, 10); // 0..9
    CHECK_EQ(r.size(), 10);
    CHECK_EQ(nc::sum(r).item(), 45);
    r.reshape(2, 5);
    CHECK_EQ(r.shape().rows, 2);
    CHECK_EQ(r.shape().cols, 5);
    nc::NdArray<int> rt = r.transpose();
    CHECK_EQ(rt.shape().rows, 5);
    CHECK_EQ(rt.shape().cols, 2);

    // ── matrix multiplication (Linalg / Core) ──
    nc::NdArray<double> A = { {1.0, 2.0}, {3.0, 4.0} };
    nc::NdArray<double> B = { {5.0, 6.0}, {7.0, 8.0} };
    nc::NdArray<double> AB = nc::dot(A, B);
    CHECK_EQ(AB.shape().rows, 2);
    CHECK_NEAR(AB(0, 0), 19.0, 1e-12);
    CHECK_NEAR(AB(0, 1), 22.0, 1e-12);
    CHECK_NEAR(AB(1, 1), 50.0, 1e-12);

    // ── Boost.Math special function (Special module, boost-backed) ──
    CHECK_NEAR(nc::special::gamma(5.0), 24.0, 1e-12);
    CHECK_NEAR(nc::special::gamma(0.5), std::sqrt(nc::constants::pi), 1e-12);

    // ── DateTime round-trip (Boost.DateTime backed) ──
    nc::DateTime dt("2024-01-02T03:04:05.123Z");
    CHECK_EQ(dt.year(), 2024);
    CHECK_EQ(dt.month(), 1);
    CHECK_EQ(dt.day(), 2);
    CHECK_EQ(dt.hour(), 3);
    CHECK_EQ(dt.minute(), 4);
    CHECK_EQ(dt.second(), 5);
    CHECK_EQ(dt.toStr(), std::string("2024-01-02T03:04:05.123Z"));

    // ── Boost.Polynomial backed helper ──
    CHECK_NEAR(nc::polynomial::chebyshev_t(2, 0.5), -0.5, 1e-12);

    // ── Random normal sanity (statistical, wide tolerance) ──
    nc::random::seed(42);
    nc::NdArray<double> gauss = nc::random::randN<double>({2000, 1});
    double mean = nc::mean(gauss).item();
    CHECK_NEAR(mean, 0.0, 0.2);

    // ── gcd/lcm fallback (std::gcd path; boost disabled only if macro set) ──
    CHECK_EQ(nc::gcd(12, 18), 6);
    CHECK_EQ(nc::lcm(4, 6), 12);

    if (failures == 0)
    {
        std::cout << "test_numcpp: all checks passed (" << assertions
                  << " assertions)" << std::endl;
        return 0;
    }
    std::cout << "test_numcpp: " << failures << " / " << assertions
              << " assertions FAILED" << std::endl;
    return 1;
}
