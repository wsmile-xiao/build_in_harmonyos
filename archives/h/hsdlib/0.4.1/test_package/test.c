/*
 * test_hsdlib.c — hsdlib 0.4.1 消费者测试
 *
 * 仅通过已安装/导出的公开头文件 <hsdlib.h> 与公开库 libhsd，模拟第三方
 * 上层使用者：编译、链接、调用公开 API 并验证可观察数值结果（R34，禁止
 * print-only 空壳）。调用公开 API:
 *   hsd_dist_sqeuclidean_f32 / hsd_dist_manhattan_f32 / hsd_dist_hamming_u8
 *   hsd_sim_dot_f32 / hsd_sim_cosine_f32 / hsd_sim_jaccard_u16
 * 每个结果与手工推导的参考值比对。
 */
#include <hsdlib.h>
#include <math.h>
#include <stdio.h>
#include <stdint.h>

static int g_failures = 0;

#define CHECK_NEAR(name, actual, expected, tol)                                     \
    do {                                                                            \
        double a = (double)(actual), e = (double)(expected);                        \
        if (fabs(a - e) > (tol)) {                                                  \
            printf("FAIL: %s actual=%f expected=%f\n", name, a, e);                 \
            ++g_failures;                                                           \
        } else {                                                                    \
            printf("PASS: %s = %f\n", name, a);                                     \
        }                                                                           \
    } while (0)

#define CHECK_EQ(name, actual, expected)                                            \
    do {                                                                            \
        uint64_t a = (uint64_t)(actual), e = (uint64_t)(expected);                  \
        if (a != e) {                                                               \
            printf("FAIL: %s actual=%llu expected=%llu\n", name,                    \
                   (unsigned long long)a, (unsigned long long)e);                   \
            ++g_failures;                                                           \
        } else {                                                                    \
            printf("PASS: %s = %llu\n", name, (unsigned long long)a);               \
        }                                                                           \
    } while (0)

int main(void) {
    hsd_status_t st;
    float result = 0.0f;

    /* 1) 平方欧氏距离: (1,2,3) vs (4,5,6) -> 27 */
    const float a1[] = {1.0f, 2.0f, 3.0f};
    const float b1[] = {4.0f, 5.0f, 6.0f};
    st = hsd_dist_sqeuclidean_f32(a1, b1, 3, &result);
    CHECK_EQ("sqeuclidean status", (uint64_t)st, 0);
    CHECK_NEAR("sqeuclidean_f32", result, 27.0, 1e-5);

    /* 2) 曼哈顿距离: 3+3+3 = 9 */
    st = hsd_dist_manhattan_f32(a1, b1, 3, &result);
    CHECK_EQ("manhattan status", (uint64_t)st, 0);
    CHECK_NEAR("manhattan_f32", result, 9.0, 1e-5);

    /* 3) 汉明距离 u8: 0xFF vs 0x00 -> 8 个 bit 不同 */
    const uint8_t h1[] = {0xFF, 0x00, 0xF0};
    const uint8_t h2[] = {0x00, 0xFF, 0xF0};
    uint64_t hres = 0;
    st = hsd_dist_hamming_u8(h1, h2, 3, &hres);
    CHECK_EQ("hamming status", (uint64_t)st, 0);
    CHECK_EQ("hamming_u8", hres, 16);

    /* 4) 点积: 4+10+18 = 32 */
    st = hsd_sim_dot_f32(a1, b1, 3, &result);
    CHECK_EQ("dot status", (uint64_t)st, 0);
    CHECK_NEAR("dot_f32", result, 32.0, 1e-5);

    /* 5) 余弦相似度: dot/(|a||b|) = 32/sqrt(14*77) = 32/sqrt(1078) */
    st = hsd_sim_cosine_f32(a1, b1, 3, &result);
    CHECK_EQ("cosine status", (uint64_t)st, 0);
    CHECK_NEAR("cosine_f32", result, 32.0 / sqrt(1078.0), 1e-5);

    /* 6) Jaccard u16（Jaccard-like: dot/(||a||²+||b||²-dot)）
     *    a={100,200,300,0} b={100,200,0,400}
     *    dot=50000, ||a||²=140000, ||b||²=210000 -> 50000/300000=0.166667 */
    const uint16_t j1[] = {100, 200, 300, 0};
    const uint16_t j2[] = {100, 200, 0, 400};
    st = hsd_sim_jaccard_u16(j1, j2, 4, &result);
    CHECK_EQ("jaccard status", (uint64_t)st, 0);
    CHECK_NEAR("jaccard_u16", result, 50000.0 / 300000.0, 1e-5);

    if (g_failures == 0) {
        printf("ALL CONSUMER TESTS PASSED\n");
        return 0;
    }
    printf("%d consumer test(s) FAILED\n", g_failures);
    return 1;
}