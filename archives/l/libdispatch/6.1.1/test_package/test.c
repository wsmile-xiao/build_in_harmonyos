#include <stdio.h>
#include <stdlib.h>
#include <dispatch/dispatch.h>
#include <string.h>

/* Consumer test for libdispatch 6.1.1: real GCD API calls with assertions. */
int main(void)
{
    int failures = 0;

    /* 1. dispatch_queue_create + dispatch_sync: verify queue label */
    {
        dispatch_queue_t q = dispatch_queue_create("test.queue", NULL);
        if (!q) {
            fprintf(stderr, "FAIL: dispatch_queue_create returned NULL\n");
            failures++;
        } else {
            const char *label = dispatch_queue_get_label(q);
            if (!label || strcmp(label, "test.queue") != 0) {
                fprintf(stderr, "FAIL: dispatch_queue_get_label mismatch\n");
                failures++;
            } else {
                printf("PASS: dispatch_queue_create + label OK\n");
            }
            dispatch_release(q);
        }
    }

    /* 2. dispatch_apply: verify all indices visited */
    {
        __block int count = 0;
        dispatch_apply(10, 0, ^(size_t i) {
            __sync_fetch_and_add(&count, 1);
        });
        if (count != 10) {
            fprintf(stderr, "FAIL: dispatch_apply count=%d (expected 10)\n", count);
            failures++;
        } else {
            printf("PASS: dispatch_apply visited all 10 iterations\n");
        }
    }

    /* 3. dispatch_once: verify it runs exactly once */
    {
        static dispatch_once_t once = 0;
        __block int once_count = 0;
        for (int i = 0; i < 5; i++) {
            dispatch_once(&once, ^{ once_count++; });
        }
        if (once_count != 1) {
            fprintf(stderr, "FAIL: dispatch_once ran %d times (expected 1)\n", once_count);
            failures++;
        } else {
            printf("PASS: dispatch_once ran exactly once\n");
        }
    }

    /* 4. dispatch_time: verify relative time calculation */
    {
        dispatch_time_t t = dispatch_time(DISPATCH_TIME_NOW, 1000000000ULL); /* 1s */
        if (t == DISPATCH_TIME_FOREVER) {
            fprintf(stderr, "FAIL: dispatch_time returned FOREVER\n");
            failures++;
        } else {
            printf("PASS: dispatch_time created relative time\n");
        }
    }

    if (failures > 0) {
        fprintf(stderr, "libdispatch consumer test: %d failure(s)\n", failures);
        return 1;
    }
    printf("libdispatch consumer test: OK\n");
    return 0;
}