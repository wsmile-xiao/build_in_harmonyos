// Conan test_package for stats 3.4.0 — real API consumer test.
// Calls StatsLib distribution functions and asserts numeric results with a
// 1e-6 relative tolerance (same tolerance as the upstream test suite).
#include <cmath>
#include <cstdio>
#include <random>

#include "stats.hpp"

namespace {

int g_failures = 0;

void check(const char* name, double actual, double expected, double tol) {
    double err = std::fabs(actual - expected) / (1.0 + std::fabs(expected));
    if (err >= tol) {
        std::printf("FAIL %s: actual=%.10Lf expected=%.10Lf err=%Le\n",
                    name, (long double)actual, (long double)expected,
                    (long double)err);
        ++g_failures;
    } else {
        std::printf("PASS %s: %.10Lf\n", name, (long double)actual);
    }
}

}  // namespace

int main() {
    // dnorm: N(1,2) density at 1.0 = 1/(2*sqrt(2*pi)) = 0.19947114020071635
    check("dnorm(1.0,1.0,2.0)", stats::dnorm(1.0, 1.0, 2.0), 0.19947114020071635, 1e-6);

    // dnorm log form: ln(0.19947114020071635) = -1.6120857137788636
    check("dnorm(1.0,1.0,2.0,log=true)",
          stats::dnorm(1.0, 1.0, 2.0, true), -1.6120857137788636, 1e-6);

    // pnorm: standard normal CDF at 0 = 0.5
    check("pnorm(0.0,0.0,1.0)", stats::pnorm(0.0, 0.0, 1.0), 0.5, 1e-9);

    // qnorm: standard normal 97.5% quantile = 1.959963984540054
    check("qnorm(0.975,0.0,1.0)", stats::qnorm(0.975, 0.0, 1.0), 1.959963984540054, 1e-6);

    // dpois: Poisson(2) pmf at 3 = e^-2 * 2^3 / 3! = 0.18044704431548358
    check("dpois(3,2.0)", stats::dpois(3, 2.0, false), 0.18044704431548358, 1e-6);

    // rnorm with a fixed seed: sample mean of 10000 draws from N(5,2)
    // must be close to 5 (statistical sanity of the generator path).
    stats::rand_engine_t engine(12345);
    double sum = 0.0;
    const int n = 10000;
    for (int i = 0; i < n; ++i) {
        sum += stats::rnorm(5.0, 2.0, engine);
    }
    double mean = sum / n;
    std::printf("rnorm seeded sample mean: %.6Lf (expected close to 5.0)\n",
                (long double)mean);
    if (std::fabs(mean - 5.0) > 0.1) {
        std::printf("FAIL rnorm sample mean out of tolerance: %.10Lf\n",
                    (long double)mean);
        ++g_failures;
    }

    if (g_failures != 0) {
        std::printf("test_stats: %d check(s) FAILED\n", g_failures);
        return 1;
    }
    std::printf("test_stats: all consumer checks passed\n");
    return 0;
}
