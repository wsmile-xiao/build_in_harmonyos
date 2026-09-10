// Consumer test — libmorton 0.2.9.
// Exercises the real libmorton API: Morton encode/decode round-trip in 2D/3D.
#include <cstdint>
#include <cstdio>
#include <cstdlib>

#include <libmorton/morton.h>

using libmorton::morton2D_64_decode;
using libmorton::morton2D_64_encode;
using libmorton::morton3D_64_decode;
using libmorton::morton3D_64_encode;

static int failures = 0;

#define CHECK(cond)                                                       \
    do {                                                                  \
        if (!(cond)) {                                                    \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);   \
            ++failures;                                                   \
        }                                                                 \
    } while (0)

int main() {
    // morton3D_64: encode then decode must round-trip for several samples.
    // Coordinates are uint_fast32_t (on aarch64 = unsigned int, 4 bytes).
    const uint_fast32_t samples3d[][3] = {
        {0, 0, 0},          {1, 0, 0},        {0, 1, 0},    {0, 0, 1},
        {5, 7, 9},          {1024, 2048, 4096},
    };
    for (const auto &s : samples3d) {
        uint_fast64_t code = morton3D_64_encode(s[0], s[1], s[2]);
        uint_fast32_t x, y, z;
        morton3D_64_decode(code, x, y, z);
        CHECK(x == s[0]);
        CHECK(y == s[1]);
        CHECK(z == s[2]);
    }

    // morton2D_64: round-trip.
    const uint_fast32_t samples2d[][2] = {
        {0, 0}, {1, 0}, {0, 1}, {3, 5}, {12345, 67890},
    };
    for (const auto &s : samples2d) {
        uint_fast64_t code = morton2D_64_encode(s[0], s[1]);
        uint_fast32_t x, y;
        morton2D_64_decode(code, x, y);
        CHECK(x == s[0]);
        CHECK(y == s[1]);
    }

    // Determinism smoke check.
    CHECK(morton3D_64_encode(5, 7, 9) == morton3D_64_encode(5, 7, 9));

    if (failures == 0) {
        std::printf("test_libmorton: all assertions passed\n");
        return 0;
    }
    std::printf("test_libmorton: %d assertion(s) failed\n", failures);
    return 1;
}