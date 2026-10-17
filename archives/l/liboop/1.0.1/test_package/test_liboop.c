/* test_liboop.c — consumer test for packaged liboop 1.0.1.
 *
 * Exercises the installed core event-loop API with six deterministic,
 * non-blocking checks. Each successful check prints exactly one
 * "CHECK-OK: <name>" line; test_package/conanfile.py counts those lines
 * for the HMBS_TEST_PACKAGE_RESULT machine marker (exit-0 alone is not
 * proof). No network, no threads, no timing flakes: timers are probed via
 * oop_sys_run on the empty loop plus one pending OOP_TIME_NOW timer via
 * run_once (never run_once on the empty loop -- it blocks), signals are
 * registered then cancelled without delivery.
 */
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "oop.h"

/* Check-4 safety note (liboop sys.c): oop_sys_run_once() on an EMPTY loop
 * blocks in select() with a NULL timeout forever -- sys.c retries EINTR
 * (do { rv = select(...); } while (rv < 0 && errno == EINTR)), so a SIGALRM
 * guard can never interrupt it. The safe probes are: oop_sys_run() on the
 * empty loop (returns immediately per docs: "no event sinks registered")
 * plus run_once() with one pending OOP_TIME_NOW timer (polls, fires
 * immediately, never blocks).
 */
static int g_timer_fired = 0;

static void *timer_cb(oop_source *src, struct timeval tv, void *data)
{
    (void) src; (void) tv; (void) data;
    return OOP_CONTINUE;
}

static void *timer_count_cb(oop_source *src, struct timeval tv, void *data)
{
    (void) src; (void) tv; (void) data;
    ++g_timer_fired;
    return OOP_CONTINUE;
}
static void *fd_cb(oop_source *src, int fd, oop_event ev, void *data)
{
    (void) src; (void) fd; (void) ev; (void) data;
    return OOP_CONTINUE;
}

static void *sig_cb(oop_source *src, int sig, void *data)
{
    (void) src; (void) sig; (void) data;
    return OOP_CONTINUE;
}

static void *select_cb(oop_adapter_select *ad, int num,
                       fd_set *r, fd_set *w, fd_set *x,
                       struct timeval now, void *data)
{
    (void) ad; (void) num; (void) r; (void) w; (void) x;
    (void) now; (void) data;
    return OOP_CONTINUE;
}

int main(void)
{
    /* Unbuffered stdout: every CHECK-OK line must reach the log even if the
     * process is later killed (SIGKILL discards stdio buffers). Each CHECK
     * below is additionally followed by fflush for the same reason.
     */
    setvbuf(stdout, NULL, _IONBF, 0);

    /* 1. System source creation. */
    oop_source_sys *sys = oop_sys_new();
    if (sys == NULL) {
        fprintf(stderr, "FAIL: oop_sys_new returned NULL\n");
        return 1;
    }
    printf("CHECK-OK: sys-new\n");
    fflush(stdout);

    /* 2. Registration interface must expose all six entry points. */
    oop_source *src = oop_sys_source(sys);
    if (src == NULL || src->on_fd == NULL || src->cancel_fd == NULL ||
        src->on_time == NULL || src->cancel_time == NULL ||
        src->on_signal == NULL || src->cancel_signal == NULL) {
        fprintf(stderr, "FAIL: oop_sys_source interface incomplete\n");
        oop_sys_delete(sys);
        return 1;
    }
    printf("CHECK-OK: sys-source-iface\n");
    fflush(stdout);

    /* 3. Custom allocator hooks are honoured. */
    {
        void *p = oop_malloc(32);
        if (p == NULL) {
            fprintf(stderr, "FAIL: oop_malloc returned NULL\n");
            oop_sys_delete(sys);
            return 1;
        }
        memset(p, 0xA5, 32);
        void *q = oop_realloc(p, 64);
        if (q == NULL) {
            fprintf(stderr, "FAIL: oop_realloc returned NULL\n");
            oop_free(p);
            oop_sys_delete(sys);
            return 1;
        }
        if (((unsigned char *) q)[0] != 0xA5) {
            fprintf(stderr, "FAIL: oop_realloc did not preserve data\n");
            oop_free(q);
            oop_sys_delete(sys);
            return 1;
        }
        oop_free(q);
    }
    printf("CHECK-OK: custom-alloc\n");
    fflush(stdout);

    /* 4. Timer schedule + cancel leaves the loop empty (oop_sys_run must
     * return immediately), then one pending OOP_TIME_NOW timer fires via
     * run_once without blocking. Never call run_once on the empty loop:
     * with no timers/fds ptv is NULL and select() blocks forever. */
    {
        void *ret;

        src->on_time(src, OOP_TIME_NOW, timer_cb, NULL);
        src->cancel_time(src, OOP_TIME_NOW, timer_cb, NULL);
        ret = oop_sys_run(sys);
        if (ret != OOP_CONTINUE) {
            fprintf(stderr, "FAIL: oop_sys_run on empty loop != OOP_CONTINUE\n");
            oop_sys_delete(sys);
            return 1;
        }
        g_timer_fired = 0;
        src->on_time(src, OOP_TIME_NOW, timer_count_cb, NULL);
        ret = oop_sys_run_once(sys);
        if (ret != OOP_CONTINUE) {
            fprintf(stderr, "FAIL: run_once with pending timer != OOP_CONTINUE\n");
            oop_sys_delete(sys);
            return 1;
        }
        if (g_timer_fired != 1) {
            fprintf(stderr, "FAIL: pending timer callback fired %d times, want 1\n",
                    g_timer_fired);
            oop_sys_delete(sys);
            return 1;
        }
    }
    printf("CHECK-OK: timer-cancel-run-once\n");
    fflush(stdout);

    /* 5. fd + signal register/cancel round-trip (pipe, SIGUSR1). */
    {
        int fds[2] = { -1, -1 };
        if (pipe(fds) != 0) {
            perror("FAIL: pipe");
            oop_sys_delete(sys);
            return 1;
        }
        src->on_fd(src, fds[0], OOP_READ, fd_cb, NULL);
        src->cancel_fd(src, fds[0], OOP_READ);
        close(fds[0]);
        close(fds[1]);
        src->on_signal(src, SIGUSR1, sig_cb, NULL);
        src->cancel_signal(src, SIGUSR1, sig_cb, NULL);
    }
    printf("CHECK-OK: fd-signal-cancel\n");
    fflush(stdout);

    /* 6. Helper adapters create/delete without a running loop. */
    {
        oop_adapter_select *sel = oop_select_new(src, select_cb, NULL);
        if (sel == NULL) {
            fprintf(stderr, "FAIL: oop_select_new returned NULL\n");
            oop_sys_delete(sys);
            return 1;
        }
        oop_select_delete(sel);
        oop_adapter_signal *sigad = oop_signal_new(src);
        if (sigad == NULL) {
            fprintf(stderr, "FAIL: oop_signal_new returned NULL\n");
            oop_sys_delete(sys);
            return 1;
        }
        if (oop_signal_source(sigad) == NULL) {
            fprintf(stderr, "FAIL: oop_signal_source returned NULL\n");
            oop_signal_delete(sigad);
            oop_sys_delete(sys);
            return 1;
        }
        oop_signal_delete(sigad);
    }
    printf("CHECK-OK: adapters\n");
    fflush(stdout);

    oop_sys_delete(sys);
    printf("ALL-OK: 6/6 liboop consumer checks passed\n");
    fflush(stdout);
    return 0;
}
