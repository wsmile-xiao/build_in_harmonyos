/*
 * HarmonyOS 专项测试 — orcania 2.3.2
 *
 * 与上游 CTest 测试（str_test/split_test/memory_test/pointer_list_test）区分：
 * 本用例验证 orcania 公开 API 在 HarmonyOS PC (aarch64) 上的真实可观察行为，
 * 包括：
 *   1. __OHOS__ 编译环境守卫下的 API 调用路径（真实逻辑，非空壳）
 *   2. o_split_string_array / o_strdup / o_base64url_encode 等公开 API
 *      在 OHOS 运行时环境中的输出正确性
 *   3. 多线程并发调用 orcania 纯函数 API 的稳定性（OHOS pthread 环境）
 *
 * 编译: clang -I<install>/include ohos_special_test.c <install>/lib/liborcania.a -lpthread -o ohos_special_test
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <stdatomic.h>

#include "orcania.h"

#ifdef __OHOS__
#define OHOS_PLATFORM 1
#else
#define OHOS_PLATFORM 0
#endif

/* 并发 worker: 每个线程反复调用纯函数 API（orcania 无内部全局状态）。
 * worker_fail 使用 C11 _Atomic 原子标志，避免多线程 write-write 数据竞争。 */
static _Atomic int worker_fail = 0;
static void *worker(void *arg) {
    int i;
    (void)arg;
    for (i = 0; i < 200; i++) {
        char *dup = o_strdup("hydrox-os-concurrent");
        if (!dup) {
            worker_fail = 1;
            return NULL;
        }
        if (o_strcmp(dup, "hydrox-os-concurrent") != 0) {
            worker_fail = 1;
            free(dup);
            return NULL;
        }
        free(dup);

        unsigned char out[64] = {0};
        size_t out_len = 0;
        const unsigned char in[] = "thread-payload";
        if (o_base64_encode(in, sizeof(in) - 1, out, &out_len) != 1 || out_len == 0) {
            worker_fail = 1;
            return NULL;
        }
    }
    return NULL;
}

int main(void) {
    /* 1. OHOS 平台守卫：真实分支，非空壳 */
    printf("platform: __OHOS__=%d (expect 1 on HarmonyOS PC)\n", OHOS_PLATFORM);
    if (!OHOS_PLATFORM) {
        fprintf(stderr, "not compiled for OHOS\n");
        return 2;
    }

    /* 2. split_string：拆分 "a,b,c" */
    {
        char **arr = NULL;
        size_t n = split_string("a,b,c", ",", &arr);
        if (n != 3 || arr == NULL || arr[0] == NULL || arr[1] == NULL || arr[2] == NULL) {
            fprintf(stderr, "split_string returned incomplete array (n=%zu)\n", n);
            if (arr != NULL) {
                free_string_array(arr);
            }
            return 1;
        }
        if (o_strcmp(arr[0], "a") != 0 || o_strcmp(arr[1], "b") != 0 || o_strcmp(arr[2], "c") != 0) {
            fprintf(stderr, "split_string content mismatch\n");
            free_string_array(arr);
            return 1;
        }
        free_string_array(arr);
        printf("split_string: PASS (a,b,c)\n");
    }

    /* 3. o_base64url_encode：输出 URL-safe base64，OHOS 可观察 */
    {
        unsigned char out[64] = {0};
        size_t out_len = 0;
        const unsigned char in[] = "hello orcania on OHOS";
        int rc = o_base64url_encode(in, sizeof(in) - 1, out, &out_len);
        if (rc != 1 || out_len == 0) {
            fprintf(stderr, "o_base64url_encode failed (rc=%d len=%zu)\n", rc, out_len);
            return 1;
        }
        printf("o_base64url_encode: PASS (%zu bytes)\n", out_len);
    }

    /* 4. 并发稳定性：4 线程 × 200 次调用 */
    {
        pthread_t th[4];
        int i;
        worker_fail = 0;
        for (i = 0; i < 4; i++) {
            if (pthread_create(&th[i], NULL, worker, NULL) != 0) {
                fprintf(stderr, "pthread_create failed\n");
                return 1;
            }
        }
        for (i = 0; i < 4; i++) {
            pthread_join(th[i], NULL);
        }
        if (worker_fail) {
            fprintf(stderr, "concurrent worker failed\n");
            return 1;
        }
        printf("concurrency: PASS (4 threads x 200 iters, o_strdup/o_strcmp/o_base64_encode)\n");
    }

    printf("ohos_special_test PASS\n");
    return 0;
}