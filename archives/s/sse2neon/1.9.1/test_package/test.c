/*
 * test_sse2neon.c — 消费者测试（sse2neon 1.9.1，header-only）
 *
 * 仅通过公开头文件 <sse2neon.h> 提供的 SSE→NEON 翻译接口，验证第三方
 * 使用者可编译、链接、调用并得到可观察结果（R34：禁止空壳/print-only）。
 * 调用公开 SIMD API: _mm_set1_ps / _mm_add_ps / _mm_mul_ps / _mm_cvtss_f32
 * 以及整数路径 _mm_add_epi32 / _mm_cvtsi128_si32，校验数值结果。
 */
#include <sse2neon.h>
#include <stdio.h>
#include <stdlib.h>

static int failures = 0;
#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            printf("FAIL: %s (line %d)\n", #cond, __LINE__);            \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main(void) {
    /* 1) 浮点 SIMD: 1.5 + 2.5 = 4.0, 1.5 * 2.5 = 3.75 */
    __m128 a = _mm_set1_ps(1.5f);
    __m128 b = _mm_set1_ps(2.5f);
    __m128 s = _mm_add_ps(a, b);
    __m128 m = _mm_mul_ps(a, b);
    float sum = _mm_cvtss_f32(s);
    float prod = _mm_cvtss_f32(m);
    CHECK(sum == 4.0f);
    CHECK(prod == 3.75f);
    printf("fp: 1.5+2.5=%.2f, 1.5*2.5=%.2f\n", sum, prod);

    /* 2) 整数 SIMD: 10 + 32 = 42 */
    __m128i ia = _mm_set1_epi32(10);
    __m128i ib = _mm_set1_epi32(32);
    __m128i isum = _mm_add_epi32(ia, ib);
    int ival = _mm_cvtsi128_si32(isum);
    CHECK(ival == 42);
    printf("int: 10+32=%d\n", ival);

    if (failures == 0) {
        printf("PASS: sse2neon 1.9.1 consumer test passed\n");
        return 0;
    }
    printf("FAILED: %d check(s) failed\n", failures);
    return 1;
}
