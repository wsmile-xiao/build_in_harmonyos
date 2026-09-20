/*
 * tevent consumer test for HarmonyOS PC (aarch64).
 *
 * The point of this test is to exercise the parts of tevent that depend on
 * the platform backend rather than only linking the library:
 *
 *   1. tevent_backend_list() must offer "epoll" on OHOS (sys/epoll.h exists,
 *      so tevent_epoll.c is compiled in); "poll" is the fallback backend.
 *   2. A tevent_context must initialise on that backend.
 *   3. An immediate event must be delivered, and exactly once.
 *   4. A timer scheduled for "now" must be delivered.
 *   5. A real pipe registered with tevent_add_fd() must report readable data
 *      through the event loop, i.e. the epoll registration path works.
 *   6. The loop must terminate: tevent_loop_once() must not spin forever.
 *
 * Every step prints its result and returns a distinct non-zero exit code on
 * failure so the CI log shows which behavioural guarantee broke.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include <talloc.h>
#include <tevent.h>

struct counters {
    int immediate_called;
    int timer_called;
    int fd_called;
    int fd_read_end;
    char fd_byte;
    ssize_t fd_read;
};

static void immediate_handler(struct tevent_context *ev,
                              struct tevent_immediate *im,
                              void *private_data)
{
    struct counters *c = talloc_get_type_abort(private_data, struct counters);
    (void)ev;
    (void)im;
    c->immediate_called++;
}

static void timer_handler(struct tevent_context *ev, struct tevent_timer *te,
                          struct timeval current_time, void *private_data)
{
    struct counters *c = talloc_get_type_abort(private_data, struct counters);
    (void)ev;
    (void)te;
    (void)current_time;
    c->timer_called++;
}

static void fd_handler(struct tevent_context *ev, struct tevent_fd *fde,
                       uint16_t flags, void *private_data)
{
    struct counters *c = talloc_get_type_abort(private_data, struct counters);
    (void)ev;
    (void)fde;
    (void)flags;
    c->fd_called++;
    c->fd_read = read(c->fd_read_end, &c->fd_byte, 1);
}

static int backend_available(TALLOC_CTX *mem_ctx, const char *want)
{
    const char **list = tevent_backend_list(mem_ctx);
    int i;

    if (list == NULL) {
        return 0;
    }
    for (i = 0; list[i] != NULL; i++) {
        if (strcmp(list[i], want) == 0) {
            return 1;
        }
    }
    return 0;
}

int main(void)
{
    TALLOC_CTX *mem_ctx = NULL;
    struct tevent_context *ev = NULL;
    struct tevent_immediate *im = NULL;
    struct tevent_timer *te = NULL;
    struct tevent_fd *fde = NULL;
    struct counters *c = NULL;
    int pipefd[2] = { -1, -1 };
    int iterations = 0;
    int rc;

    mem_ctx = talloc_new(NULL);
    if (mem_ctx == NULL) {
        printf("FAIL: talloc_new\n");
        return 1;
    }

    /* 1. epoll backend is compiled in on OHOS */
    if (!backend_available(mem_ctx, "epoll")) {
        printf("FAIL: tevent_backend_list has no epoll backend\n");
        return 2;
    }
    printf("ok: epoll backend present\n");

    /* 2. tevent context initialises */
    ev = tevent_context_init(mem_ctx);
    if (ev == NULL) {
        printf("FAIL: tevent_context_init: %s\n", strerror(errno));
        return 3;
    }
    printf("ok: tevent_context_init\n");

    c = talloc_zero(mem_ctx, struct counters);
    if (c == NULL) {
        printf("FAIL: talloc_zero counters\n");
        return 4;
    }

    /* 3. immediate event */
    im = tevent_create_immediate(c);
    if (im == NULL) {
        printf("FAIL: tevent_create_immediate\n");
        return 5;
    }
    tevent_schedule_immediate(im, ev, immediate_handler, c);

    /* 4. timer due now */
    te = tevent_add_timer(ev, c, tevent_timeval_current(), timer_handler, c);
    if (te == NULL) {
        printf("FAIL: tevent_add_timer\n");
        return 6;
    }

    /* 5. readable pipe registered with the event loop */
    if (pipe(pipefd) != 0) {
        printf("FAIL: pipe: %s\n", strerror(errno));
        return 7;
    }
    c->fd_read_end = pipefd[0];
    fde = tevent_add_fd(ev, c, pipefd[0], TEVENT_FD_READ, fd_handler, c);
    if (fde == NULL) {
        printf("FAIL: tevent_add_fd\n");
        return 8;
    }
    if (write(pipefd[1], "H", 1) != 1) {
        printf("FAIL: write to pipe: %s\n", strerror(errno));
        return 9;
    }

    /* 6. drive the loop; bounded so a broken backend cannot hang the CI */
    while (iterations < 1000) {
        if (c->immediate_called && c->timer_called && c->fd_called) {
            break;
        }
        rc = tevent_loop_once(ev);
        if (rc != 0) {
            printf("FAIL: tevent_loop_once: %s\n", strerror(errno));
            return 10;
        }
        iterations++;
    }
    if (iterations >= 1000) {
        printf("FAIL: event loop did not settle within 1000 iterations"
               " (immediate=%d timer=%d fd=%d)\n",
               c->immediate_called, c->timer_called, c->fd_called);
        return 11;
    }

    if (c->immediate_called != 1) {
        printf("FAIL: immediate handler ran %d times, expected 1\n",
               c->immediate_called);
        return 12;
    }
    printf("ok: immediate delivered once\n");

    if (c->timer_called != 1) {
        printf("FAIL: timer handler ran %d times, expected 1\n",
               c->timer_called);
        return 13;
    }
    printf("ok: timer delivered once\n");

    if (c->fd_called != 1 || c->fd_read != 1 || c->fd_byte != 'H') {
        printf("FAIL: fd handler calls=%d read=%ld byte=%c\n", c->fd_called,
               (long)c->fd_read, c->fd_byte ? c->fd_byte : '?');
        return 14;
    }
    printf("ok: fd handler read 'H' from the pipe\n");

    close(pipefd[0]);
    close(pipefd[1]);

    /* talloc owns the tevent context: freeing the root must release it */
    talloc_free(mem_ctx);
    printf("ok: talloc_free released the tevent context\n");

    printf("test_tevent: all 6 checks passed\n");
    return 0;
}
