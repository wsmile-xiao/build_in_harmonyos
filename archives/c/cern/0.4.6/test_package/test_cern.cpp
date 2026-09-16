#include <cmath>
#include <cstdio>

#include "vdt/vdtMath.h"

static int check_close(const char *name, double got, double ref, double tol) {
    double diff = std::fabs(got - ref);
    if (diff > tol) {
        std::fprintf(stderr, "FAIL %s: got %f ref %f diff %f\n", name, got, ref, diff);
        return 1;
    }
    std::printf("PASS %s: got %f ref %f\n", name, got, ref);
    return 0;
}

int main() {
    int failures = 0;
    failures += check_close("fast_exp(1.0)", vdt::fast_exp(1.0), std::exp(1.0), 1e-3);
    failures += check_close("fast_expf(1.0f)", vdt::fast_expf(1.0f), std::exp(1.0f), 1e-3f);
    failures += check_close("fast_sin(0.5)", vdt::fast_sin(0.5), std::sin(0.5), 1e-4);
    failures += check_close("fast_cos(0.5)", vdt::fast_cos(0.5), std::cos(0.5), 1e-4);
    failures += check_close("fast_log(2.0)", vdt::fast_log(2.0), std::log(2.0), 1e-4);
    {
        const unsigned int n = 4;
        double input[n] = {0.0, 0.5, 1.0, 2.0};
        double output[n] = {0.0, 0.0, 0.0, 0.0};
        vdt::fast_expv(n, input, output);
        for (unsigned int i = 0; i < n; ++i) {
            char name[64];
            std::snprintf(name, sizeof(name), "fast_expv[%u]", i);
            failures += check_close(name, output[i], std::exp(input[i]), 1e-3);
        }
    }
    if (failures != 0) {
        std::fprintf(stderr, "test_cern FAILED: %d failures\n", failures);
        return 1;
    }
    std::printf("test_cern PASSED: 9 assertions\n");
    return 0;
}
