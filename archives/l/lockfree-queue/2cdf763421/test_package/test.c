/*
 * test_package consumer test for lockfree-queue 2cdf763421.
 * Calls the real lock-free queue API (init_queue/queue_add/queue_get)
 * in a single-threaded producer/consumer round-trip.
 */
#include <stdio.h>
#include <stdlib.h>

#include "pkt_queue.h"

int main(void) {
    struct queue_root *queue = NULL;
    int values[100];
    int i, ok = 1;

    init_queue(&queue);
    if (queue == NULL) {
        printf("init_queue failed\n");
        return 1;
    }

    for (i = 0; i < 100; i++) {
        values[i] = i * 7;
        if (!queue_add(queue, &values[i])) {
            printf("queue_add failed at %d\n", i);
            return 1;
        }
    }

    for (i = 0; i < 100; i++) {
        int *val = (int *)queue_get(queue);
        if (val == NULL || *val != i * 7) {
            printf("queue_get mismatch at %d (got %p)\n", i, (void *)val);
            ok = 0;
            break;
        }
    }

    if (ok && queue_get(queue) != NULL) {
        printf("queue not empty after draining\n");
        ok = 0;
    }

    printf("test lockfree-queue 2cdf763421: %s\n", ok ? "OK" : "FAIL");
    return ok ? 0 : 1;
}
