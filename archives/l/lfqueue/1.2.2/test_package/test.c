/* test_package consumer test for lfqueue 1.2.2 (HarmonyOS PC / OHOS).
 *
 * Real consumer test: exercises the public lfqueue API through the
 * installed header and linked library. A producer thread enqueues
 * NITEMS integers; a consumer thread dequeues exactly NITEMS items
 * with lfqueue_deq_must (blocking variant). Verifies the FIFO checksum,
 * queue size accounting and destruction. Only public API + public
 * header are used.
 */
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "lfqueue.h"

#define NITEMS 100000

static lfqueue_t g_queue;

static void *producer(void *arg) {
    (void)arg;
    int i;
    for (i = 0; i < NITEMS; i++) {
        int *v = (int *)malloc(sizeof(int));
        if (v == NULL) { fprintf(stderr, "malloc failed\n"); exit(2); }
        *v = i;
        while (lfqueue_enq(&g_queue, v) != 0) {
            /* retry until enqueued */
        }
    }
    return NULL;
}

static void *consumer(void *arg) {
    long *sum = (long *)arg;
    int i;
    for (i = 0; i < NITEMS; i++) {
        int *v = (int *)lfqueue_deq_must(&g_queue);
        *sum += *v;
        free(v);
    }
    return NULL;
}

int main(void) {
    pthread_t t1, t2;
    long sum = 0;
    size_t n;
    long expected = (long)(NITEMS - 1) * NITEMS / 2;

    if (lfqueue_init(&g_queue) != 0) {
        fprintf(stderr, "lfqueue_init failed\n");
        return 1;
    }
    if (pthread_create(&t1, NULL, producer, NULL) != 0) return 1;
    if (pthread_create(&t2, NULL, consumer, &sum) != 0) return 1;
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);

    n = lfqueue_size(&g_queue);
    printf("lfqueue consumer: enqueued %d, sum=%ld (expected %ld), size=%zu\n",
           NITEMS, sum, expected, n);
    if (n != 0) {
        fprintf(stderr, "queue not empty after consume: %zu\n", n);
        return 1;
    }
    if (sum != expected) {
        fprintf(stderr, "checksum mismatch\n");
        return 1;
    }
    lfqueue_destroy(&g_queue);
    printf("lfqueue consumer test PASSED\n");
    return 0;
}
