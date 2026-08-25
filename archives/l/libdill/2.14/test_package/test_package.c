/* libdill test_package consumer — exercises core structured-concurrency APIs.
 *
 * No network, no external ports, no random data: fully deterministic.
 * Links against libdill, uses channel + coroutine + time APIs, prints checks.
 */
#include <libdill.h>
#include <stdio.h>
#include <string.h>

/* Coroutine: compute sum of 1..n and send result through channel end. */
coroutine static void sum_worker(int ch, int n) {
    int sum = 0;
    for (int i = 1; i <= n; i++) {
        sum += i;
    }
    int rc = chsend(ch, &sum, sizeof(sum), -1);
    (void)rc;
    chdone(ch);
}

/* Coroutine: echo a fixed integer back through the channel. */
coroutine static void echo_worker(int ch) {
    int val = 0;
    int rc = chrecv(ch, &val, sizeof(val), -1);
    if (rc == 0) {
        chsend(ch, &val, sizeof(val), -1);
    }
    chdone(ch);
}

int main(void) {
    int checks = 0;
    int failures = 0;

    /* ---- Check 1: chmake creates a channel pair ---- */
    int ch[2];
    if (chmake(ch) != 0) {
        printf("FAIL 1: chmake returned error\n");
        failures++;
    } else {
        printf("CHECK 1: chmake OK\n");
        checks++;
    }

    /* ---- Check 2: go + chsend + chrecv (coroutine communication) ---- */
    go(sum_worker(ch[0], 100));
    int result = 0;
    if (chrecv(ch[1], &result, sizeof(result), -1) != 0 || result != 5050) {
        printf("FAIL 2: chrecv got %d (expected 5050)\n", result);
        failures++;
    } else {
        printf("CHECK 2: coroutine channel send/recv OK (sum 1..100 = %d)\n", result);
        checks++;
    }
    hclose(ch[0]);
    hclose(ch[1]);

    /* ---- Check 3: bidirectional channel (send then echo back) ---- */
    int ch2[2];
    if (chmake(ch2) != 0) {
        printf("FAIL 3a: chmake returned error\n");
        failures++;
    } else {
        go(echo_worker(ch2[0]));
        int val = 42;
        if (chsend(ch2[1], &val, sizeof(val), -1) != 0) {
            printf("FAIL 3b: chsend error\n");
            failures++;
        } else {
            int echoed = 0;
            if (chrecv(ch2[1], &echoed, sizeof(echoed), -1) != 0 || echoed != 42) {
                printf("FAIL 3c: echo recv got %d (expected 42)\n", echoed);
                failures++;
            } else {
                printf("CHECK 3: bidirectional channel echo OK (sent %d, got %d)\n", val, echoed);
                checks++;
            }
        }
        hclose(ch2[0]);
        hclose(ch2[1]);
    }

    /* ---- Check 4: now() + msleep() (clock/time API) ---- */
    int64_t t0 = now();
    msleep(now() + 50); /* sleep ~50 ms */
    int64_t t1 = now();
    if (t1 - t0 < 40) {
        printf("FAIL 4: msleep slept only %lld ms\n", (long long)(t1 - t0));
        failures++;
    } else {
        printf("CHECK 4: now/msleep OK (%lld ms elapsed)\n", (long long)(t1 - t0));
        checks++;
    }

    /* ---- Summary ---- */
    printf("\n%d checks passed, %d failures.\n", checks, failures);
    if (failures > 0) {
        printf("RESULT: FAILED\n");
        return 1;
    }
    printf("RESULT: All checks passed.\n");
    return 0;
}
