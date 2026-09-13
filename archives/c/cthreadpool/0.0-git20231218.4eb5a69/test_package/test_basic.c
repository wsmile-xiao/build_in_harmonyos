#include <pthread.h>
#include <stdio.h>

#include "thpool.h"

static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;
static int g_sum = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);     \
            return 1;                                                          \
        }                                                                      \
        g_checks++;                                                            \
    } while (0)

static void increment(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&g_mutex);
    g_sum++;
    pthread_mutex_unlock(&g_mutex);
}

int main(void)
{
    threadpool pool = thpool_init(4);
    CHECK(pool != NULL);
    for (int i = 0; i < 200; i++) {
        CHECK(thpool_add_work(pool, increment, NULL) == 0);
    }
    thpool_wait(pool);
    CHECK(g_sum == 200);
    CHECK(thpool_num_threads_working(pool) == 0);
    thpool_destroy(pool);
    printf("CTHREADPOOL_TEST basic PASS checks=%d\n", g_checks);
    return 0;
}
