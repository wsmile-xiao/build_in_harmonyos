#include <cmath>
#include <cstdio>

#include <geodesic.h>
#include <proj.h>

static int check_close(const char *name, double actual, double expected) {
    if (std::fabs(actual - expected) > 1e-9) {
        std::printf("FAIL: %s expected %.12f, got %.12f\n", name, expected, actual);
        return 1;
    }
    return 0;
}

int main() {
    int errors = 0;

    const PJ_INFO info = proj_info();
    if (info.version == nullptr || info.version[0] == '\0') {
        std::puts("FAIL: proj_info() returned an empty version");
        ++errors;
    }

    PJ_CONTEXT *ctx = proj_context_create();
    if (ctx == nullptr) {
        std::puts("FAIL: proj_context_create() returned null");
        return 1;
    }

    PJ *swap = proj_create(ctx, "+proj=pipeline +step +proj=axisswap +order=2,1");
    if (swap == nullptr) {
        std::puts("FAIL: proj_create() could not create axis-swap pipeline");
        proj_context_destroy(ctx);
        return 1;
    }

    PJ_COORD in = proj_coord(12.0, 55.0, 0.0, 0.0);
    PJ_COORD out = proj_trans(swap, PJ_FWD, in);
    errors += check_close("axis swap x", out.xy.x, 55.0);
    errors += check_close("axis swap y", out.xy.y, 12.0);
    if (proj_errno(swap) != 0) {
        std::printf("FAIL: proj_errno() returned %d\n", proj_errno(swap));
        ++errors;
    }

    PJ *invalid = proj_create(ctx, "+proj=definitely_missing");
    if (invalid != nullptr) {
        std::puts("FAIL: invalid projection unexpectedly succeeded");
        proj_destroy(invalid);
        ++errors;
    }

    struct geod_geodesic geod;
    double distance = 0.0;
    double azi1 = 0.0;
    double azi2 = 0.0;
    geod_init(&geod, 6378137.0, 1.0 / 298.257223563);
    geod_inverse(&geod, 0.0, 0.0, 0.0, 1.0, &distance, &azi1, &azi2);
    if (distance < 111000.0 || distance > 112000.0) {
        std::printf("FAIL: geodesic distance out of range: %.6f\n", distance);
        ++errors;
    }

    proj_destroy(swap);
    proj_context_destroy(ctx);

    if (errors != 0) {
        std::printf("FAIL: %d PROJ checks failed\n", errors);
        return 1;
    }

    std::puts("ALL PROJ TESTS PASSED");
    return 0;
}
