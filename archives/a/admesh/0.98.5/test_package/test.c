#include <math.h>
#include <stdio.h>

#include <stl.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    stl_facet facet = {0};
    float normal[3] = {0.0f, 0.0f, 0.0f};

    facet.vertex[0].x = 0.0f;
    facet.vertex[0].y = 0.0f;
    facet.vertex[0].z = 0.0f;
    facet.vertex[1].x = 1.0f;
    facet.vertex[1].y = 0.0f;
    facet.vertex[1].z = 0.0f;
    facet.vertex[2].x = 0.0f;
    facet.vertex[2].y = 1.0f;
    facet.vertex[2].z = 0.0f;

    stl_calculate_normal(normal, &facet);
    CHECK(fabsf(normal[0]) < 0.0001f, "normal x is zero");
    CHECK(fabsf(normal[1]) < 0.0001f, "normal y is zero");
    CHECK(fabsf(normal[2] - 1.0f) < 0.0001f, "normal z is one");

    stl_normalize_vector(normal);
    CHECK(fabsf(normal[2] - 1.0f) < 0.0001f, "normalized vector is stable");

    printf("PASS: admesh normal=(%.1f,%.1f,%.1f)\n", normal[0], normal[1], normal[2]);
    return 0;
}
