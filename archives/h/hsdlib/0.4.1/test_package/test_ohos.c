/*
 * test_ohos.c — hsdlib 0.4.1 鸿蒙专项测试（HarmonyOS aarch64）
 *
 * 验证 hsdlib 在 OHOS 平台的核心适配点：运行时 SIMD 后端调度
 * （AUTO/SCALAR/NEON/SVE，经 HWCAP 探测）确认真实可用：
 *   1. AUTO 模式下后端字符串非空且可打印（实测为 "Auto (NEON Capable)"）
 *   2. hsd_has_avx512() 在非 x86 平台返回 false（平台探针正确）
 *   3. 强制 SCALAR 后端与 AUTO 后端计算同一输入得到一致结果
 *      （运行时调度切换真实生效）
 *   4. 强制 NEON 后端（AArch64 存在）结果同样一致
 */
#include <hsdlib.h>
#include <math.h>
#include <stdio.h>

static int g_failures = 0;

#define REQUIRE(cond)                                                               \
    do {                                                                            \
        if (!(cond)) {                                                              \
            printf("FAIL: %s (line %d)\n", #cond, __LINE__);                        \
            ++g_failures;                                                           \
        } else {                                                                    \
            printf("PASS: %s\n", #cond);                                            \
        }                                                                           \
    } while (0)

int main(void) {
    /* 构造一个稍大的随机输入，避免单后端特化 */
    enum { N = 64 };
    float a[N], b[N];
    for (int i = 0; i < N; ++i) {
        a[i] = (float)((i * 7) % 13) + 0.5f;
        b[i] = (float)((i * 3) % 11) - 0.25f;
    }

    /* 1) AUTO 后端探测非空（OHOS 实测 "Auto (NEON Capable)"）*/
    const char* backend = hsd_get_backend();
    REQUIRE(backend != NULL && backend[0] != '\0');
    if (backend) {
        printf("INFO: backend = \"%s\"\n", backend);
    }

    /* 2) 非 x86 平台 hsd_has_avx512() 必须为 false（探针正确性）*/
#if defined(__aarch64__)
    REQUIRE(hsd_has_avx512() == false);
#endif

    /* 3) AUTO vs SCALAR vs NEON 结果一致性 */
    float r_auto = 0.0f, r_scalar = 0.0f, r_neon = 0.0f;
    hsd_status_t st;

    st = hsd_sim_cosine_f32(a, b, N, &r_auto);
    REQUIRE(st == HSD_SUCCESS);

    st = hsd_set_manual_backend(HSD_BACKEND_SCALAR);
    REQUIRE(st == HSD_SUCCESS);
    st = hsd_sim_cosine_f32(a, b, N, &r_scalar);
    REQUIRE(st == HSD_SUCCESS);
    REQUIRE(fabs(r_auto - r_scalar) < 1e-6f);

    st = hsd_set_manual_backend(HSD_BACKEND_NEON);
    REQUIRE(st == HSD_SUCCESS);
    st = hsd_sim_cosine_f32(a, b, N, &r_neon);
    REQUIRE(st == HSD_SUCCESS);
    REQUIRE(fabs(r_auto - r_neon) < 1e-6f);

    /* 4) 恢复 AUTO，验证距离函数跨后端一致 */
    st = hsd_set_manual_backend(HSD_BACKEND_AUTO);
    REQUIRE(st == HSD_SUCCESS);
    float d_auto = 0.0f, d_scalar = 0.0f;
    st = hsd_dist_sqeuclidean_f32(a, b, N, &d_auto);
    REQUIRE(st == HSD_SUCCESS);
    st = hsd_set_manual_backend(HSD_BACKEND_SCALAR);
    REQUIRE(st == HSD_SUCCESS);
    st = hsd_dist_sqeuclidean_f32(a, b, N, &d_scalar);
    REQUIRE(st == HSD_SUCCESS);
    REQUIRE(fabs(d_auto - d_scalar) < 1e-5f);

    printf("INFO: cosine(auto)=%f cosine(scalar)=%f cosine(neon)=%f\n",
           r_auto, r_scalar, r_neon);
    printf("INFO: sqeuclidean(auto)=%f sqeuclidean(scalar)=%f\n", d_auto, d_scalar);

    if (g_failures == 0) {
        printf("ALL OHOS SPECIAL TESTS PASSED\n");
        return 0;
    }
    printf("%d OHOS special test(s) FAILED\n", g_failures);
    return 1;
}