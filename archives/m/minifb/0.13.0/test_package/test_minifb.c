/* Consumer test for minifb 0.13.0 (headless OHOS core) — exercises the
 * software-framebuffer contract that works without a window system:
 * 1. mfb_update state machine with NULL/invalid windows (documented
 *    error paths — the window creation itself is the headless-excluded
 *    surface);
 * 2. the full timer API backed by the OHOS clock_gettime bridge:
 *    mfb_timer_create/reset/now/delta/destroy + set/get target fps;
 * 3. mfb_get_key_data / mfb_get_mouse_data zero-state sanity. */
#include <stdio.h>
#include <math.h>

#include <MiniFB.h>

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("ok: %s\n", msg); } \
} while (0)

int main(void)
{
    /* ---- 1. update state machine (NULL window → documented error) ---- */
    unsigned int buf[8 * 8];
    mfb_update_state st = mfb_update(NULL, buf);
    CHECK(st == MFB_STATE_INVALID_WINDOW, "mfb_update(NULL) -> INVALID_WINDOW");

    /* ---- 2. timer API (OHOS clock_gettime bridge) ---- */
    mfb_set_target_fps(60);
    CHECK(mfb_get_target_fps() == 60, "set/get target fps 60");

    struct mfb_timer *tmr = mfb_timer_create();
    CHECK(tmr != NULL, "mfb_timer_create");

    /* busy-wait a little so the clock advances */
    volatile double acc = 0.0;
    for (int i = 0; i < 2000000; i++)
        acc += 1.0;

    double now1 = mfb_timer_now(tmr);
    CHECK(now1 >= 0.0, "mfb_timer_now >= 0");
    printf("timer now: %.6f s\n", now1);

    double d1 = mfb_timer_delta(tmr);
    CHECK(d1 >= 0.0, "mfb_timer_delta >= 0");

    mfb_timer_reset(tmr);
    double now2 = mfb_timer_now(tmr);
    CHECK(now2 < 1.0, "timer reset -> now small");

    /* elapsed scaling sanity: now() should advance with wall time */
    for (int i = 0; i < 2000000; i++)
        acc += 1.0;
    double d2 = mfb_timer_delta(tmr);
    CHECK(d2 > 0.0, "timer delta advances with wall time");

    mfb_timer_destroy(tmr);

    /* ---- 3. input getters tolerate NULL window (documented contract) ---- */
    CHECK(mfb_get_mouse_x(NULL) == 0, "mfb_get_mouse_x(NULL) == 0");
    CHECK(mfb_get_mouse_y(NULL) == 0, "mfb_get_mouse_y(NULL) == 0");
    CHECK(mfb_get_mouse_scroll_x(NULL) == 0.0f, "mfb_get_mouse_scroll_x(NULL) == 0");

    /* timer frequency/resolution from the clock_gettime bridge */
    double freq = mfb_timer_get_frequency();
    CHECK(freq > 0.0, "mfb_timer_get_frequency > 0");
    double res = mfb_timer_get_resolution();
    CHECK(res > 0.0 && res < 1.0, "mfb_timer_get_resolution in (0,1)");

    printf("failures=%d\n", failures);
    return failures ? 1 : 0;
}
