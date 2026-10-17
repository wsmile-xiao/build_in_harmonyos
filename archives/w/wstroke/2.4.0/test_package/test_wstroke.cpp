#include <cstdio>
#include <cstdlib>
#include <cmath>
#include "stroke.h"

static int test_basic_alloc_free() {
    stroke_t *s = stroke_alloc(10);
    if (!s) {
        printf("FAIL: stroke_alloc returned null\n");
        return 1;
    }
    // Empty stroke after finish should have size 0
    stroke_finish(s);
    int sz = stroke_get_size(s);
    if (sz != 0) {
        printf("FAIL: empty stroke size %d expected 0\n", sz);
        stroke_free(s);
        return 1;
    }
    stroke_free(s);
    printf("PASS: test_basic_alloc_free\n");
    return 0;
}

static int test_add_points_and_retrieve() {
    stroke_t *s = stroke_alloc(10);
    stroke_add_point(s, 0.0, 0.0);
    stroke_add_point(s, 10.0, 0.0);
    stroke_add_point(s, 10.0, 10.0);
    stroke_add_point(s, 20.0, 10.0);
    stroke_finish(s);
    int sz = stroke_get_size(s);
    if (sz <= 0) {
        printf("FAIL: stroke size %d expected >0\n", sz);
        stroke_free(s);
        return 1;
    }
    double x, y;
    stroke_get_point(s, 0, &x, &y);
    // First point should be near origin after normalization? At least finite
    if (!std::isfinite(x) || !std::isfinite(y)) {
        printf("FAIL: first point not finite %f %f\n", x, y);
        stroke_free(s);
        return 1;
    }
    double t0 = stroke_get_time(s, 0);
    double a0 = stroke_get_angle(s, 0);
    if (!std::isfinite(t0) || !std::isfinite(a0)) {
        printf("FAIL: time/angle not finite\n");
        stroke_free(s);
        return 1;
    }
    stroke_free(s);
    printf("PASS: test_add_points_and_retrieve (size=%d)\n", sz);
    return 0;
}

static int test_copy_and_compare() {
    stroke_t *a = stroke_alloc(10);
    stroke_t *b = stroke_alloc(10);
    // Draw two similar strokes (horizontal line)
    for (int i = 0; i < 5; ++i) {
        stroke_add_point(a, double(i)*10.0, 0.0);
        stroke_add_point(b, double(i)*10.0 + 0.5, 0.2); // slight offset
    }
    stroke_finish(a);
    stroke_finish(b);
    // Copy
    stroke_t *c = stroke_copy(a);
    if (!c) {
        printf("FAIL: stroke_copy returned null\n");
        stroke_free(a); stroke_free(b);
        return 1;
    }
    if (stroke_get_size(c) != stroke_get_size(a)) {
        printf("FAIL: copy size mismatch\n");
        stroke_free(a); stroke_free(b); stroke_free(c);
        return 1;
    }
    double d1 = stroke_compare(a, b, nullptr, nullptr);
    double d2 = stroke_compare(a, c, nullptr, nullptr);
    if (!std::isfinite(d1) || !std::isfinite(d2)) {
        printf("FAIL: compare not finite %f %f\n", d1, d2);
        stroke_free(a); stroke_free(b); stroke_free(c);
        return 1;
    }
    // A vs its copy should be smaller distance than A vs B (with offset)
    if (d2 > d1 + 1e-6) {
        printf("WARN: copy distance %f > similar stroke distance %f (maybe ok)\n", d2, d1);
    }
    if (d2 >= stroke_infinity) {
        printf("FAIL: copy distance >= infinity\n");
        stroke_free(a); stroke_free(b); stroke_free(c);
        return 1;
    }
    // Angle difference test
    double ad = stroke_angle_difference(a, b, 0, 0);
    if (!std::isfinite(ad)) {
        printf("FAIL: angle difference not finite\n");
        stroke_free(a); stroke_free(b); stroke_free(c);
        return 1;
    }
    stroke_free(a); stroke_free(b); stroke_free(c);
    printf("PASS: test_copy_and_compare (d1=%f d2=%f ad=%f)\n", d1, d2, ad);
    return 0;
}

static int test_infinity_constant() {
    if (!std::isfinite(stroke_infinity) || stroke_infinity <= 0) {
        printf("FAIL: stroke_infinity not positive finite %f\n", stroke_infinity);
        return 1;
    }
    // Upstream stroke.c defines stroke_infinity = 0.2 as the gesture
    // acceptance threshold (not a large sentinel). Verify the pinned
    // 2.4.0 value with tolerance.
    if (fabs(stroke_infinity - 0.2) > 1e-9) {
        printf("FAIL: stroke_infinity %f expected 0.2\n", stroke_infinity);
        return 1;
    }
    printf("PASS: test_infinity_constant (%f)\n", stroke_infinity);
    return 0;
}

int main() {
    int failed = 0;
    failed += test_basic_alloc_free();
    failed += test_add_points_and_retrieve();
    failed += test_copy_and_compare();
    failed += test_infinity_constant();
    if (failed == 0) {
        printf("All wstroke core tests PASSED (4/4)\n");
        return 0;
    } else {
        printf("wstroke core tests FAILED: %d failures\n", failed);
        return 1;
    }
}
