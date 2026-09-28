/*
 * test_package consumer test — lwbtn 1.3.2
 *
 * R34: must substantively call the package API. lwbtn is a button
 * state-machine library: we register one button, drive the state
 * machine with lwbtn_process(), simulate a press+release and assert
 * that an ONCLICK event is delivered to the event callback.
 */
#include <stdio.h>
#include <string.h>
#include "lwbtn/lwbtn.h"

static uint8_t btn_state = 0;
static unsigned click_count = 0;

static uint8_t
get_state_fn(struct lwbtn* lwobj, struct lwbtn_btn* btn) {
    (void)lwobj;
    (void)btn;
    return btn_state;
}

static void
evt_fn(struct lwbtn* lwobj, struct lwbtn_btn* btn, lwbtn_evt_t evt) {
    (void)lwobj;
    (void)btn;
    if (evt == LWBTN_EVT_ONCLICK) {
        ++click_count;
    }
}

int
main(void) {
    lwbtn_btn_t btn;
    memset(&btn, 0, sizeof(btn));

    if (lwbtn_init(&btn, 1, get_state_fn, evt_fn) != 1) {
        printf("test lwbtn 1.3.2: FAIL (init)\n");
        return 1;
    }

    /*
     * Defaults: DEBOUNCE_PRESS=20, CLICK_MIN=20, CLICK_MAX=300,
     * CLICK_MULTI_MAX=400 (lwbtn_opt.h).
     * lwbtn_process(mstime) takes an ABSOLUTE millisecond timestamp;
     * the library computes elapsed time internally.
     * NOTE: the library requires the FIRST observed button state to be
     * inactive (LWBTN_FLAG_FIRST_INACTIVE_RCVD), so start with 10ms
     * inactive before pressing.
     */
    /* 10ms inactive first */
    lwbtn_process(10);
    /* Press (active) for 40ms, then release 440ms (> click_multi_max). */
    btn_state = 1;
    for (unsigned t = 20; t < 60; t += 10) {
        lwbtn_process(t);
    }
    btn_state = 0;
    for (unsigned t = 60; t < 500; t += 10) {
        lwbtn_process(t);
    }

    if (click_count == 0) {
        printf("test lwbtn 1.3.2: FAIL (no click event)\n");
        return 1;
    }
    printf("test lwbtn 1.3.2: OK (click_count=%u)\n", click_count);
    return 0;
}
