#define CUTE_C2_IMPLEMENTATION
#include "cute_c2.h"

#include <math.h>
#include <stdio.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main(void) {
    int failures = 0;
    c2Circle circle = { { 0.0f, 0.0f }, 2.0f };
    c2AABB box = { { -1.0f, -1.0f }, { 1.0f, 1.0f } };

    CHECK(c2AABBtoAABB(box, box), "an AABB intersects itself");
    CHECK(c2CircletoAABB(circle, box), "a circle intersects an AABB");
    CHECK(c2CircletoCircle(circle, circle), "a circle intersects itself");
    CHECK(fabsf(c2Len(c2V(3.0f, 4.0f)) - 5.0f) < 0.001f,
          "vector length is computed correctly");

    if (failures != 0) {
        fprintf(stderr, "cute_headers consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    puts("cute_headers consumer test passed: 4 assertions");
    return 0;
}