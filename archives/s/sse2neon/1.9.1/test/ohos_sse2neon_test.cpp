// ohos_sse2neon_test.cpp — HarmonyOS 专项测试（sse2neon 1.9.1）
//
// 目的：验证 sse2neon.h 在 HarmonyOS aarch64（OHOS clang 15 + musl）下
// 通过 NEON 翻译路径真实可编译、可链接、可运行，且结果正确。
// 平台特异性：静态断言 SSE2NEON_ARCH_AARCH64（确保走 NEON 实现而非
// 未知回退分支），并在运行时校验浮点/整数 SIMD 计算的可观察结果。
#include <sse2neon.h>
#include <cstdio>
#include <cstdint>
#include <cstring>

// 仅 AArch64 编译，确保测试的是 NEON 翻译路径
#if !defined(SSE2NEON_ARCH_AARCH64) && !defined(__aarch64__)
#error "ohos_sse2neon_test must be compiled on AArch64 (NEON) target"
#endif

static int failures = 0;
#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);       \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main() {
    // 1) 浮点四路 SIMD 加法：{1,2,3,4} + {4,3,2,1} = {5,5,5,5}
    __m128 a = _mm_set_ps(1.0f, 2.0f, 3.0f, 4.0f);
    __m128 b = _mm_set_ps(4.0f, 3.0f, 2.0f, 1.0f);
    __m128 s = _mm_add_ps(a, b);
    float r[4];
    _mm_storeu_ps(r, s);
    CHECK(r[0] == 5.0f && r[1] == 5.0f && r[2] == 5.0f && r[3] == 5.0f);

    // 2) 整数运算路径：_mm_add_epi32 逐 lane 校验
    // _mm_set_epi32(w,z,y,x) 低→高 lane 为 {x,y,z,w}
    __m128i ia = _mm_set_epi32(100, 10, 0, -5);
    __m128i ib = _mm_set1_epi32(5);
    __m128i is = _mm_add_epi32(ia, ib);          // {0,5,15,105}
    CHECK(_mm_cvtsi128_si32(is) == 0);           // lane 0: -5 + 5
    CHECK(_mm_extract_epi32(is, 3) == 105);      // lane 3: 100 + 5

    // 3) 位运算/置换：_mm_shuffle_ps 选择 a 低 lane（即 4.0）到 dst[0]
    // _mm_set_ps(1,2,3,4) → 低→高 lane 为 {4,3,2,1}，a[0] = 4.0
    __m128 sh = _mm_shuffle_ps(a, _mm_set1_ps(9.0f), 0x00);
    float sr[4];
    _mm_storeu_ps(sr, sh);
    CHECK(sr[0] == 4.0f);

    // 4) 与 C 接口混用（OHOS 下 printf 打印 SIMD 标量结果）
    float sum = _mm_cvtss_f32(_mm_add_ps(_mm_set1_ps(1.5f), _mm_set1_ps(2.5f)));
    std::printf("OHOS 专项测试: 1.5+2.5=%g\n", sum);
    CHECK(sum == 4.0f);

    if (failures == 0) {
        std::printf("PASS: sse2neon 1.9.1 HarmonyOS 专项测试全部通过\n");
        return 0;
    }
    std::printf("FAILED: %d check(s) failed\n", failures);
    return 1;
}