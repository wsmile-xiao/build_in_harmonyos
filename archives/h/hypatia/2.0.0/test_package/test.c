#include <stdio.h>
#include <assert.h>

#define HYPATIA_IMPLEMENTATION
#include <hypatia.h>

int main(void) {
    struct vector3 a;
    struct vector3 b;
    struct vector3 r;

    printf("Using Hypatia Version: %s\n", HYPATIA_VERSION);

    vector3_setf3(&a, 3.0f, -3.0f, 1.0f);
    vector3_setf3(&b, 4.0f, 9.0f, 2.0f);

    vector3_cross_product(&r, &a, &b);

    assert(scalar_equalsf(r.x, -15.0f));
    assert(scalar_equalsf(r.y, -2.0f));
    assert(scalar_equalsf(r.z, 39.0f));

    printf("hypatia 2.0.0 test: cross product verified OK\n");
    return 0;
}
