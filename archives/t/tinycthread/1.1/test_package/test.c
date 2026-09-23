/* test_package consumer test — tinycthread 1.1
 * 实际调用被测库 API（R34 反空壳）：4 线程 × 1000 次互斥锁保护计数，
 * 验证 thrd_create/thrd_join/mtx_init/mtx_lock/mtx_unlock/mtx_destroy。
 */
#include <stdio.h>
#include <tinycthread.h>

#define THREAD_COUNT 4
#define ITER_COUNT 1000

static mtx_t g_mtx;
static int g_count = 0;

static int worker(void *arg) {
    (void)arg;
    for (int i = 0; i < ITER_COUNT; ++i) {
        if (mtx_lock(&g_mtx) != thrd_success) return 1;
        ++g_count;
        if (mtx_unlock(&g_mtx) != thrd_success) return 1;
    }
    return 0;
}

int main(void) {
    thrd_t threads[THREAD_COUNT];
    if (mtx_init(&g_mtx, mtx_plain) != thrd_success) {
        printf("FAIL: mtx_init\n");
        return 1;
    }
    for (int i = 0; i < THREAD_COUNT; ++i) {
        if (thrd_create(&threads[i], worker, NULL) != thrd_success) {
            printf("FAIL: thrd_create\n");
            return 1;
        }
    }
    for (int i = 0; i < THREAD_COUNT; ++i) {
        int res = 0;
        if (thrd_join(threads[i], &res) != thrd_success || res != 0) {
            printf("FAIL: thrd_join\n");
            return 1;
        }
    }
    mtx_destroy(&g_mtx);
    if (g_count != THREAD_COUNT * ITER_COUNT) {
        printf("FAIL: count=%d (expected %d)\n", g_count, THREAD_COUNT * ITER_COUNT);
        return 1;
    }
    printf("tinycthread 1.1 test OK: %d increments across %d threads\n",
           g_count, THREAD_COUNT);
    return 0;
}
