/* xcb-util-keysyms 0.4.1 consumer link + API smoke test.
 *
 * Exercises the xcb-util-keysyms API. The keysym classification helpers
 * (xcb_is_keypad_key, xcb_is_function_key, xcb_is_cursor_key, ...) are
 * pure functions that do not require an X server connection, so they are
 * the ideal smoke-test surface. xcb_key_symbols_alloc needs a live
 * connection, so it is not exercised here (no X server on the OHOS
 * worker, mirroring the upstream make check limitation).
 */

#include <stdio.h>
#include <xcb/xcb.h>
#include <xcb/xcb_keysyms.h>

int main(void) {
    /* 1. xcb_is_keypad_key: KP_1 (0xffb1) is a keypad key. */
    if (!xcb_is_keypad_key(0xffb1)) {
        fprintf(stderr, "xcb_is_keypad_key(0xffb1) != 1\n");
        return 1;
    }

    /* 2. xcb_is_keypad_key: plain 'a' is not a keypad key. */
    if (xcb_is_keypad_key('a')) {
        fprintf(stderr, "xcb_is_keypad_key('a') != 0\n");
        return 2;
    }

    /* 3. xcb_is_function_key: F1 (0xffbe) is a function key. */
    if (!xcb_is_function_key(0xffbe)) {
        fprintf(stderr, "xcb_is_function_key(0xffbe) != 1\n");
        return 3;
    }

    /* 4. xcb_is_cursor_key: Left (0xff51) is a cursor key. */
    if (!xcb_is_cursor_key(0xff51)) {
        fprintf(stderr, "xcb_is_cursor_key(0xff51) != 1\n");
        return 4;
    }

    /* 5. xcb_is_modifier_key: Shift_L (0xffe1) is a modifier key. */
    if (!xcb_is_modifier_key(0xffe1)) {
        fprintf(stderr, "xcb_is_modifier_key(0xffe1) != 1\n");
        return 5;
    }

    /* 6. xcb_is_private_keypad_key: a normal key is not a private keypad. */
    if (xcb_is_private_keypad_key(0xffbe)) {
        fprintf(stderr, "xcb_is_private_keypad_key(F1) != 0\n");
        return 6;
    }

    if (printf("xcb-util-keysyms api smoke ok\n") < 0) {
        return 7;
    }
    return 0;
}