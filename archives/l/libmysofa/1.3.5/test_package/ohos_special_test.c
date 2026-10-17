/*
 * HarmonyOS PC (aarch64-linux-ohos) 专项测试 — libmysofa 1.3.5
 *
 * 独立于上游测试（不复述上游用例），针对 OHOS 平台验证：
 *   1) SOFA 文件真实加载（mysofa_open）与 err/filterlength 语义
 *   2) 球坐标/笛卡尔坐标往返（mysofa_c2s / mysofa_s2c）
 *   3) 任意方向 HRTF 滤波器获取（mysofa_getfilter_float）输出为有限值
 *   4) minphase / resample 处理路径在 OHOS 工具链下的数值稳定性
 *   5) 多线程并发读取同一 HRTF（pthread 路径，OHOS libc++ 线程安全）
 * 任一检查失败则以非零退出码返回，由 conan create 的 test() 捕获。
 *
 * NOTE: uses CHECK() instead of assert() so the validation still runs under
 * Release (-DNDEBUG) builds — assert() is compiled out by NDEBUG, which would
 * otherwise make the test validate nothing in CI.
 */
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mysofa.h"

#define CHECK(expr)                                                     \
    do {                                                                \
        if (!(expr)) {                                                  \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,     \
                    #expr);                                             \
            return 1;                                                   \
        }                                                               \
    } while (0)

static int test_open_and_metadata(void) {
    struct MYSOFA_EASY *easy;
    int err = 0;
    int filterlength = 0;

    easy = mysofa_open("data/testfile.sofa", 48000, &filterlength, &err);
    CHECK(easy != NULL);
    CHECK(err == 0);
    CHECK(filterlength > 0);
    CHECK(easy->hrtf != NULL);
    CHECK(easy->hrtf->M > 0);   /* 测量位置数 */
    CHECK(easy->hrtf->N > 0);   /* 滤波器长度 */
    CHECK(easy->hrtf->R >= 2);  /* 双耳通道 */
    CHECK(easy->lookup != NULL);

    printf("  [open] PASS (M=%d N=%d R=%d)\n", easy->hrtf->M,
           easy->hrtf->N, easy->hrtf->R);
    mysofa_close(easy);
    return 0;
}

static int test_coordinate_roundtrip(void) {
    /* 球坐标 (az=30°, el=45°, r=1) -> 笛卡尔 -> 球坐标，应精确往返 */
    float s[3] = {30.0f, 45.0f, 1.0f};
    float orig[3] = {30.0f, 45.0f, 1.0f};

    mysofa_s2c(s);
    mysofa_c2s(s);
    CHECK(fabsf(s[0] - orig[0]) < 1e-3f);
    CHECK(fabsf(s[1] - orig[1]) < 1e-3f);
    CHECK(fabsf(s[2] - orig[2]) < 1e-3f);

    /* 正前方 (0°, 0°, 1) -> 笛卡尔应为 +X 轴 (1, 0, 0) */
    float f[3] = {0.0f, 0.0f, 1.0f};
    mysofa_s2c(f);
    CHECK(fabsf(f[0] - 1.0f) < 1e-3f);
    CHECK(fabsf(f[1] - 0.0f) < 1e-3f);
    CHECK(fabsf(f[2] - 0.0f) < 1e-3f);

    printf("  [coordinate_roundtrip] PASS\n");
    return 0;
}

static int test_getfilter_finite(void) {
    struct MYSOFA_EASY *easy;
    int err = 0;
    int filterlength = 0;
    int i;

    easy = mysofa_open("data/testfile.sofa", 48000, &filterlength, &err);
    CHECK(easy != NULL);

    {
        float *ir_l = (float *)malloc(easy->hrtf->N * sizeof(float));
        float *ir_r = (float *)malloc(easy->hrtf->N * sizeof(float));
        float delay_l = 0.0f, delay_r = 0.0f;
        CHECK(ir_l != NULL && ir_r != NULL);

        /* 正前方 0°,0° 请求滤波器 */
        float coord[3] = {0.0f, 0.0f, 1.0f};
        mysofa_s2c(coord);
        mysofa_getfilter_float(easy, coord[0], coord[1], coord[2], ir_l,
                               ir_r, &delay_l, &delay_r);

        for (i = 0; i < easy->hrtf->N; i++) {
            CHECK(isfinite(ir_l[i]));
            CHECK(isfinite(ir_r[i]));
        }
        CHECK(isfinite(delay_l));
        CHECK(isfinite(delay_r));
        CHECK(delay_l >= 0.0f);

        free(ir_l);
        free(ir_r);
    }

    printf("  [getfilter_finite] PASS\n");
    mysofa_close(easy);
    return 0;
}

static int test_minphase_resample(void) {
    struct MYSOFA_EASY *easy;
    int err = 0;
    int filterlength = 0;

    /* 不同采样率触发 resample 路径 */
    easy = mysofa_open("data/testfile.sofa", 44100, &filterlength, &err);
    CHECK(easy != NULL);
    CHECK(filterlength > 0);

    err = mysofa_minphase(easy->hrtf, 0.01);
    /* mysofa_minphase 成功时返回截断后的新滤波器长度 max（正整数），
       失败（DataDelay 非双通道）时才返回 -1 */
    CHECK(err >= 0);

    printf("  [minphase+resample] PASS\n");
    mysofa_close(easy);
    return 0;
}

struct MT_ARGS {
    struct MYSOFA_EASY *easy;
    int failed;
};

static void *mt_thread(void *arg) {
    struct MT_ARGS *a = (struct MT_ARGS *)arg;
    int i;
    for (i = 0; i < 50; i++) {
        float *ir_l = (float *)malloc(a->easy->hrtf->N * sizeof(float));
        float *ir_r = (float *)malloc(a->easy->hrtf->N * sizeof(float));
        float delay_l = 0.0f, delay_r = 0.0f;
        float coord[3] = {0.0f, 0.0f, 1.0f};
        int j;
        if (!ir_l || !ir_r) {
            a->failed = 1;
            free(ir_l);
            free(ir_r);
            return NULL;
        }
        mysofa_s2c(coord);
        mysofa_getfilter_float(a->easy, coord[0], coord[1], coord[2], ir_l,
                               ir_r, &delay_l, &delay_r);
        for (j = 0; j < a->easy->hrtf->N; j++) {
            if (!isfinite(ir_l[j]) || !isfinite(ir_r[j])) {
                a->failed = 1;
                break;
            }
        }
        free(ir_l);
        free(ir_r);
        if (a->failed)
            break;
    }
    return NULL;
}

static int test_multithread(void) {
    struct MYSOFA_EASY *easy;
    int err = 0;
    int filterlength = 0;
    enum { T = 8 };
    pthread_t threads[T];
    struct MT_ARGS args[T];
    int t;

    easy = mysofa_open("data/testfile.sofa", 48000, &filterlength, &err);
    CHECK(easy != NULL);

    for (t = 0; t < T; t++) {
        args[t].easy = easy;
        args[t].failed = 0;
        CHECK(pthread_create(&threads[t], NULL, mt_thread, &args[t]) == 0);
    }
    for (t = 0; t < T; t++) {
        pthread_join(threads[t], NULL);
        CHECK(args[t].failed == 0);
    }

    printf("  [multithread] PASS\n");
    mysofa_close(easy);
    return 0;
}

int main(int argc, char **argv) {
    printf("HarmonyOS special test (libmysofa 1.3.5) start\n");
    if (test_open_and_metadata() != 0)
        return 1;
    if (test_coordinate_roundtrip() != 0)
        return 1;
    if (test_getfilter_finite() != 0)
        return 1;
    if (test_minphase_resample() != 0)
        return 1;
    if (test_multithread() != 0)
        return 1;
    printf("HarmonyOS special test: ALL PASSED\n");
    return 0;
}
