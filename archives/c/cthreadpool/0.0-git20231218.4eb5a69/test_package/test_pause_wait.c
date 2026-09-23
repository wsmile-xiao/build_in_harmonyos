#include <pthread.h>
#include <stdio.h>
#include <unistd.h>

#include "thpool.h"

static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;
static int g_done = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);     \
            return 1;                                                          \
        }                                                                      \
        g_checks++;                                                            \
    } while (0)

static void mark(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&g_mutex);
    g_done++;
    pthread_mutex_unlock(&g_mutex);
}

static int read_done(void)
{
    int value;
    pthread_mutex_lock(&g_mutex);
    value = g_done;
    pthread_mutex_unlock(&g_mutex);
    return value;
}

int main(void)
{
    threadpool pool = thpool_init(2);
    CHECK(pool != NULL);
    /* Workers install the SIGUSR1 handler before thpool_init returns;
       the extra pause lets every worker park in the hold loop. */
    sleep(1);
    thpool_pause(pool);
    sleep(1);
    for (int i = 0; i < 50; i++) {
        CHECK(thpool_add_work(pool, mark, NULL) == 0);
    }
    sleep(2);
    CHECK(read_done() == 0);
    thpool_resume(pool);
    thpool_wait(pool);
    CHECK(read_done() == 50);
    CHECK(thpool_num_threads_working(pool) == 0);
    thpool_destroy(pool);
    printf("CTHREADPOOL_TEST pause-wait PASS checks=%d\n", g_checks);
    return 0;
}
