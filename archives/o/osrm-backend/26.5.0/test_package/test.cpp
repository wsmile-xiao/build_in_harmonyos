#include <cmath>
#include <cstdio>
#include <string>

#include <osrm/util/bearing.hpp>
#include <osrm/util/coordinate.hpp>

static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::printf("CONSUMER CHECK FAILED: %s (line %d)\n", #cond,        \
                        __LINE__);                                             \
            return 1;                                                          \
        }                                                                      \
        g_checks++;                                                            \
    } while (0)

int main() {
    // Real osrm::util API assertions on the installed headers.

    // util::bearing: CheckInBounds(A,B,range) = is A within B+/-range, modulo-360
    CHECK(osrm::util::bearing::CheckInBounds(5, 5, 10));
    CHECK(osrm::util::bearing::CheckInBounds(355, 5, 10));
    CHECK(!osrm::util::bearing::CheckInBounds(-6, 5, 10));
    CHECK(!osrm::util::bearing::CheckInBounds(20, 5, 10));
    CHECK(osrm::util::bearing::CheckInBounds(0, 350, 20));

    // util::bearing::reverse: 180-degree flip with wrap-around
    CHECK(osrm::util::bearing::reverse(0.) == 180.);
    CHECK(osrm::util::bearing::reverse(270.) == 90.);

    // util::bearing::angleBetween: turn circle angle between two bearings
    CHECK(osrm::util::bearing::angleBetween(0., 45.) == 135.);
    CHECK(osrm::util::bearing::angleBetween(90., 135.) == 135.);

    // util::Coordinate + FloatLatitude/FloatLongitude value semantics
    osrm::util::Coordinate c1{osrm::util::FloatLongitude{13.737262},
                              osrm::util::FloatLatitude{51.050408}};
    osrm::util::Coordinate c2{c1};
    CHECK(c1 == c2);
    CHECK(!(c1 != c2));
    c2 = osrm::util::Coordinate{osrm::util::FloatLongitude{0.},
                                osrm::util::FloatLatitude{0.}};
    CHECK(c1 != c2);
    CHECK(c2.IsValid());

    std::printf("test_osrm_backend consumer: OK (%d checks)\n", g_checks);
    return 0;
}
