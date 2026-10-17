#include <stdio.h>
#include <ev.h>

static int timer_fired = 0;

static void timer_cb(EV_P_ ev_timer *watcher, int revents) {
    (void)watcher;
    (void)revents;
    timer_fired = 1;
    ev_break(EV_A_ EVBREAK_ONE);
}

int main(void) {
    printf("libev version: %d.%d\n", ev_version_major(), ev_version_minor());
    if (ev_version_major() != 4 || ev_version_minor() != 33) {
        fprintf(stderr, "Unexpected libev version\n");
        return 1;
    }

    struct ev_loop *loop = ev_default_loop(0);
    if (!loop) {
        fprintf(stderr, "Failed to create default loop\n");
        return 2;
    }

    ev_timer timer;
    ev_timer_init(&timer, timer_cb, 0.001, 0.0);
    ev_timer_start(loop, &timer);
    ev_run(loop, 0);
    if (!timer_fired) {
        fprintf(stderr, "Timer callback did not fire\n");
        ev_loop_destroy(loop);
        return 3;
    }

    ev_loop_destroy(loop);
    printf("Default loop and timer callback passed\n");
    return 0;
}
