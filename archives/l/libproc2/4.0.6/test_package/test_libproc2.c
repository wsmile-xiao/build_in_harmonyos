/*
 * test_libproc2.c — R34 substantive consumer test for the packaged libproc2.
 *
 * Links against the packaged libproc2.a and calls the real public API through
 * the upstream-documented include path (man/procps_pids.3: `#include
 * <libproc2/pids.h>`):
 *   - procps_uptime(double *, double *)                     (libproc2/misc.h)
 *   - procps_loadavg(double *, double *, double *)          (libproc2/misc.h)
 *   - procps_pids_new / procps_pids_get / procps_pids_unref (libproc2/pids.h)
 *
 * Assertion semantics follow the upstream test suite
 * (library/tests/test_uptime.c, library/tests/test_pids.c): a successful call
 * returns 0 and the fetched values are sane.
 */
#include <stdio.h>

#include <libproc2/misc.h>   /* procps_uptime, procps_loadavg */
#include <libproc2/pids.h>   /* pids API, PIDS_VAL */

static int check_uptime(void)
{
    double up = 0.0, idle = 0.0;
    int rc = procps_uptime(&up, &idle);
    if (rc != 0) {
        fprintf(stderr, "FAIL: procps_uptime() rc=%d (expected 0)\n", rc);
        return 1;
    }
    if (up <= 0.0 || idle <= 0.0) {
        fprintf(stderr, "FAIL: procps_uptime() up=%f idle=%f (expected >0)\n",
                up, idle);
        return 1;
    }
    printf("procps_uptime: up=%.1fs idle=%.1fs\n", up, idle);
    return 0;
}

static int check_loadavg(void)
{
    double av1 = -1.0, av5 = -1.0, av15 = -1.0;
    int rc = procps_loadavg(&av1, &av5, &av15);
    if (rc != 0) {
        fprintf(stderr, "FAIL: procps_loadavg() rc=%d (expected 0)\n", rc);
        return 1;
    }
    if (av1 < 0.0) {
        fprintf(stderr, "FAIL: procps_loadavg() av1=%f (expected >=0)\n", av1);
        return 1;
    }
    printf("procps_loadavg: %.2f %.2f %.2f\n", av1, av5, av15);
    return 0;
}

static int check_pids(void)
{
    enum pids_item items[] = { PIDS_ID_PID };
    struct pids_info *info = NULL;
    struct pids_stack *stack;
    int pids_seen = 0;

    if (procps_pids_new(&info, items, 1) != 0) {
        fprintf(stderr, "FAIL: procps_pids_new() != 0\n");
        return 1;
    }
    while ((stack = procps_pids_get(info, PIDS_FETCH_TASKS_ONLY)) != NULL) {
        /* items[0] == PIDS_ID_PID -> relative index 0, s_int result */
        int pid = PIDS_VAL(0, s_int, stack);
        if (pid > 0)
            pids_seen++;
    }
    if (procps_pids_unref(&info) != 0) {
        fprintf(stderr, "FAIL: procps_pids_unref() != 0\n");
        return 1;
    }
    if (pids_seen <= 0) {
        fprintf(stderr, "FAIL: procps_pids_get() fetched no PIDs\n");
        return 1;
    }
    printf("pids API: %d PIDs fetched via PIDS_ID_PID\n", pids_seen);
    return 0;
}

int main(void)
{
    if (check_uptime() != 0)
        return 1;
    if (check_loadavg() != 0)
        return 1;
    if (check_pids() != 0)
        return 1;
    printf("libproc2 4.0.6 C API: all checks passed\n");
    return 0;
}
