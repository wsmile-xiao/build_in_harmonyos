// R34: 实质调用 highway SIMD API 验证链通
#include <cstdio>
#include <vector>

#include "hwy/highway.h"
#include "hwy/foreach_target.h"

namespace HWY_NAMESPACE {

int test_simd_vector_add() {
    using DF = hwy::HWY_NAMESPACE::ScalableTag<double>;
    DF df;
    const int N = Lanes(df);

    // 动态分配数组，确保 N > 4 时（例如 SVE/AVX-512）不会越界
    std::vector<double> a_vec(N), b_vec(N), c_vec(N);
    for (int i = 0; i < N && i < 4; i++) {
        a_vec[i] = static_cast<double>(i + 1);
        b_vec[i] = static_cast<double>(i + 5);
    }
    // N>4 时剩余位置补 0
    double *a = a_vec.data();
    double *b = b_vec.data();
    double *c = c_vec.data();

    for (int i = 0; i < N; i += N) {
        auto va = LoadU(df, a + i);
        auto vb = LoadU(df, b + i);
        auto vc = Add(va, vb);
        StoreU(vc, df, c + i);
    }

    bool ok = true;
    for (int i = 0; i < N; i++) {
        if (c[i] != a[i] + b[i]) {
            printf("  ✗ SIMD vector add[%d]: %f + %f = %f (expected %f)\n",
                   i, a[i], b[i], c[i], a[i] + b[i]);
            ok = false;
        }
    }
    if (ok) {
        printf("  ✓ SIMD vector add (Lanes=%d): [%f,%f] + [%f,%f] = [%f,%f]\n",
               N, a[0], a[1], b[0], b[1], c[0], c[1]);
    }
    return ok ? 0 : 1;
}

int test_simd_caps() {
#if defined(__aarch64__)
    printf("  ✓ Platform: AARCH64 (HWY_TARGET=%lld)\n", (long long)HWY_TARGET);
#elif defined(__x86_64__) || defined(__i386__)
    printf("  ✓ Platform: X86 (HWY_TARGET=%lld)\n", (long long)HWY_TARGET);
#else
    printf("  ✓ Platform: other (HWY_TARGET=%lld)\n", (long long)HWY_TARGET);
#endif
    return 0;
}

}  // namespace HWY_NAMESPACE

HWY_EXPORT(test_simd_vector_add);
HWY_EXPORT(test_simd_caps);

int main() {
    int passed = 0, failed = 0;

    printf("Highway SIMD Test Suite\n");
    printf("======================\n\n");

    if (HWY_STATIC_DISPATCH(test_simd_vector_add)() == 0) passed++;
    else failed++;

    if (HWY_STATIC_DISPATCH(test_simd_caps)() == 0) passed++;
    else failed++;

    printf("\n========== Summary ==========\n");
    printf("Tests: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
