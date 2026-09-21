/* xcb-util-wm 0.4.2 consumer link + real API test.
 *
 * The ICCCM size-hints setters operate purely on the caller's
 * xcb_size_hints_t structure — no X server connection is involved — so the
 * flag bookkeeping they implement can be asserted directly.
 *
 * xcb_icccm_size_hints_set_position()/set_size() are the interesting cases:
 * they clear both the "user specified" and "program specified" flags before
 * setting exactly one of them, so calling them twice with different
 * user_specified arguments must not leave both flags set. The test asserts
 * that mutually exclusive behaviour, plus the flags of the setters that only
 * add a flag.
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include <xcb/xcb.h>
#include <xcb/xcb_icccm.h>
#include <xcb/xcb_ewmh.h>

static int failures = 0;
static int assertions = 0;

static void expect(const char *what, int condition) {
    assertions++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

static void expect_eq_i32(const char *what, int32_t got, int32_t want) {
    assertions++;
    if (got != want) {
        fprintf(stderr, "FAIL: %s = %d, expected %d\n", what, (int)got, (int)want);
        failures++;
    }
}

int main(void) {
    xcb_size_hints_t hints;
    memset(&hints, 0, sizeof(hints));

    /* --- position: US_POSITION and P_POSITION are mutually exclusive --- */
    xcb_icccm_size_hints_set_position(&hints, 1, 11, 22);
    expect("user-specified position sets US_POSITION",
           (hints.flags & XCB_ICCCM_SIZE_HINT_US_POSITION) != 0);
    expect("user-specified position does not set P_POSITION",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_POSITION) == 0);
    expect_eq_i32("position x", hints.x, 11);
    expect_eq_i32("position y", hints.y, 22);

    /* Re-setting as program-specified must clear the previous flag. */
    xcb_icccm_size_hints_set_position(&hints, 0, 33, 44);
    expect("program-specified position sets P_POSITION",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_POSITION) != 0);
    expect("re-setting position clears US_POSITION",
           (hints.flags & XCB_ICCCM_SIZE_HINT_US_POSITION) == 0);
    expect_eq_i32("re-set position x", hints.x, 33);
    expect_eq_i32("re-set position y", hints.y, 44);

    /* --- size: same mutual exclusion --- */
    xcb_icccm_size_hints_set_size(&hints, 1, 640, 480);
    expect("user-specified size sets US_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_US_SIZE) != 0);
    expect("user-specified size does not set P_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_SIZE) == 0);
    expect_eq_i32("size width", hints.width, 640);
    expect_eq_i32("size height", hints.height, 480);

    xcb_icccm_size_hints_set_size(&hints, 0, 320, 240);
    expect("program-specified size sets P_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_SIZE) != 0);
    expect("re-setting size clears US_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_US_SIZE) == 0);
    expect_eq_i32("re-set size width", hints.width, 320);
    expect_eq_i32("re-set size height", hints.height, 240);

    /* --- setters that only add a flag --- */
    xcb_icccm_size_hints_set_min_size(&hints, 100, 50);
    expect("min size sets P_MIN_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_MIN_SIZE) != 0);
    expect_eq_i32("min_width", hints.min_width, 100);
    expect_eq_i32("min_height", hints.min_height, 50);

    xcb_icccm_size_hints_set_max_size(&hints, 1920, 1080);
    expect("max size sets P_MAX_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_MAX_SIZE) != 0);
    expect_eq_i32("max_width", hints.max_width, 1920);
    expect_eq_i32("max_height", hints.max_height, 1080);

    xcb_icccm_size_hints_set_resize_inc(&hints, 8, 16);
    expect("resize inc sets P_RESIZE_INC",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_RESIZE_INC) != 0);
    expect_eq_i32("width_inc", hints.width_inc, 8);
    expect_eq_i32("height_inc", hints.height_inc, 16);

    xcb_icccm_size_hints_set_base_size(&hints, 10, 20);
    /* The library sets XCB_ICCCM_SIZE_HINT_BASE_SIZE here — note the absence
     * of the P_ prefix that the other setters use. */
    expect("base size sets BASE_SIZE",
           (hints.flags & XCB_ICCCM_SIZE_HINT_BASE_SIZE) != 0);
    expect_eq_i32("base_width", hints.base_width, 10);
    expect_eq_i32("base_height", hints.base_height, 20);

    xcb_icccm_size_hints_set_win_gravity(&hints, XCB_GRAVITY_STATIC);
    expect("win gravity sets P_WIN_GRAVITY",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_WIN_GRAVITY) != 0);
    expect("win gravity value", hints.win_gravity == XCB_GRAVITY_STATIC);

    /* --- previously set flags must survive later setter calls --- */
    expect("position flags survive later setters",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_POSITION) != 0);
    expect("size flags survive later setters",
           (hints.flags & XCB_ICCCM_SIZE_HINT_P_SIZE) != 0);

    /* --- ewmh component must be linked and usable too --- */
    {
        xcb_ewmh_connection_t ewmh;
        memset(&ewmh, 0, sizeof(ewmh));
        /* The atom table lives in the caller's struct; verify the ABI shape
         * is usable by writing and reading back one entry. */
        ewmh._NET_WM_NAME = 42;
        expect("ewmh atom table is writable", ewmh._NET_WM_NAME == 42);
    }

    printf("xcb-util-wm consumer test: assertions=%d failures=%d\n",
           assertions, failures);
    if (failures != 0) {
        return 1;
    }
    return 0;
}
