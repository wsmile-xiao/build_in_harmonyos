/**
 *  @brief Header-only consumer test for NumKong on OHOS.
 *
 *  NumKong can also be consumed without the dispatch library by including
 *  the headers directly (compiler-intrinsic based target detection).  This
 *  test compiles a NEON kernel through the public header to validate that
 *  the installed header tree is self-contained for the header-only path.
 */
#include <cmath>
#include <cstdio>

#include "numkong/numkong.hpp"

int main() {
    /* Header-only path: call the typed C++ wrapper around nk_dot_f32. */
    float a[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    float b[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    double result = 0.0;
    nk_dot_f32(a, b, 4, &result);
    if (std::fabs(result - 10.0) > 1e-9) {
        std::printf("FAIL: header-only nk_dot_f32 = %f, expected 10.0\n", result);
        return 1;
    }
    std::printf("header-only nk_dot_f32 = %f\n", result);

    /* Scalar helpers are header-only too: nk_f32_sqrt. */
    if (std::fabs(nk_f32_sqrt(4.0f) - 2.0f) > 1e-6) {
        std::printf("FAIL: nk_f32_sqrt(4) != 2\n");
        return 2;
    }
    std::printf("All NumKong header-only checks passed.\n");
    return 0;
}
