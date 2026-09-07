#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <poll.h>

#include "loom.h"

static volatile int completed_mask;

static void task(void *env)
{
    unsigned int index = (unsigned int)(uintptr_t)env;
    __sync_or_and_fetch(&completed_mask, 1 << index);
}

static void cleanup_pool(struct loom *pool)
{
    while (!loom_shutdown(pool)) {
        poll(NULL, 0, 1);
    }
    loom_free(pool);
}

int main(void)
{
    loom_config config = {
        .init_threads = 1,
        .max_threads = 2,
    };
    struct loom *pool = NULL;
    if (loom_init(&config, &pool) != LOOM_INIT_RES_OK || pool == NULL) {
        fprintf(stderr, "loom_init failed\n");
        return 1;
    }

    for (uintptr_t i = 0; i < 4; ++i) {
        loom_task item = { task, NULL, (void *)i };
        size_t backpressure = 0;
        int retries = 0;
        while (!loom_enqueue(pool, &item, &backpressure)) {
            if (++retries == 1000) {
                fprintf(stderr, "loom_enqueue failed at task %lu\n",
                        (unsigned long)i);
                cleanup_pool(pool);
                return 2;
            }
            poll(NULL, 0, 1);
        }
    }

    for (int waited = 0; waited < 5000; ++waited) {
        if (__sync_add_and_fetch(&completed_mask, 0) == 0x0F) {
            break;
        }
        poll(NULL, 0, 1);
    }
    if (__sync_add_and_fetch(&completed_mask, 0) != 0x0F) {
        fprintf(stderr, "not all unique tasks completed\n");
        cleanup_pool(pool);
        return 3;
    }

    loom_info info;
    if (!loom_get_stats(pool, &info) || info.backlog_size != 0) {
        fprintf(stderr, "loom queue did not drain\n");
        cleanup_pool(pool);
        return 4;
    }
    cleanup_pool(pool);
    puts("loom consumer smoke test: 4 unique tasks passed");
    return 0;
}
