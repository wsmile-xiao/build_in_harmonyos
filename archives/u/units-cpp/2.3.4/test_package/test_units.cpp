// Consumer test for the header-only units-cpp package.
// Uses the installed package through CMakeDeps + find_package(units).
// The checks are HarmonyOS-specific consumer cases written for this
// adaptation; the expected values are ported from upstream unitTests/main.cpp.
#include <chrono>
#include <cmath>
#include <cstdio>
#include <string>

#include <units.h>

using namespace units;
using namespace units::length;
using namespace units::mass;
using namespace units::time;
using namespace units::temperature;
using namespace units::energy;
using namespace units::power;
using namespace units::velocity;
using namespace units::data;
using namespace units::math;
using namespace units::literals;

static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                          \
        }                                                                      \
    } while (0)

#define CHECK_NEAR(actual, expect, eps)                                        \
    do {                                                                       \
        ++g_checks;                                                            \
        const double a_ = static_cast<double>(actual);                         \
        const double e_ = static_cast<double>(expect);                         \
        if (std::fabs(a_ - e_) > (eps)) {                                      \
            std::fprintf(stderr, "FAIL %s:%d: |%g - %g| > %g\n",               \
                         __FILE__, __LINE__, a_, e_, (double)(eps));           \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main() {
    // length conversions
    CHECK_NEAR(meter_t(1.0).convert<feet>().to<double>(), 3.28084, 1.0e-5);
    CHECK_NEAR(kilometer_t(1.0).convert<meter>().to<double>(), 1000.0, 1.0e-9);
    CHECK_NEAR(mile_t(1.0).convert<meter>().to<double>(), 1609.344, 1.0e-6);

    // user-defined literals
    CHECK_NEAR((2.5_m).to<double>(), 2.5, 1.0e-12);
    CHECK_NEAR((1_km).convert<meter>().to<double>(), 1000.0, 1.0e-9);

    // affine temperature conversions
    CHECK_NEAR(celsius_t(100.0).convert<fahrenheit>().to<double>(), 212.0, 1.0e-9);
    CHECK_NEAR(fahrenheit_t(32.0).convert<celsius>().to<double>(), 0.0, 1.0e-9);

    // mass / time
    CHECK_NEAR((convert<kilograms, grams>(1.0)), 1000.0, 1.0e-9);
    CHECK_NEAR(minute_t(1.0).convert<second>().to<double>(), 60.0, 1.0e-9);

    // decimal vs binary data units
    CHECK_NEAR(byte_t(1).convert<bit>().to<double>(), 8.0, 1.0e-9);
    CHECK_NEAR(kilobyte_t(1.0).convert<byte>().to<double>(), 1000.0, 1.0e-9);
    CHECK_NEAR(kibibyte_t(1.0).convert<byte>().to<double>(), 1024.0, 1.0e-9);

    // energy / power
    CHECK_NEAR((convert<kilojoules, joules>(1.0)), 1000.0, 1.0e-9);
    CHECK_NEAR((convert<kilowatts, watts>(1.0)), 1000.0, 1.0e-9);

    // compound velocity conversion
    CHECK_NEAR((convert<meters_per_second, kilometers_per_hour>(1.0)), 3.6, 1.0e-6);

    // arithmetic on unit containers
    meter_t sum = meter_t(2.0) + meter_t(3.0);
    CHECK_NEAR(sum.to<double>(), 5.0, 1.0e-12);

    // formatting and type erasure
    CHECK(units::length::to_string(meter_t(8)) == "8 m");
    CHECK_NEAR(units::unit_cast<double>(meter_t(5.0)), 5.0, 1.0e-12);

    // std::chrono interoperability (time units expose a nanoseconds conversion)
    std::chrono::nanoseconds chrono_ns = second_t(1);
    CHECK(chrono_ns.count() == 1000000000LL);
    nanosecond_t from_chrono = std::chrono::nanoseconds(250);
    CHECK_NEAR(from_chrono.to<double>(), 250.0, 1.0e-9);

    std::printf("units-cpp consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
