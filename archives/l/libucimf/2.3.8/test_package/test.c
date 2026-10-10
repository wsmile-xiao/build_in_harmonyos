/*
 * test_package consumer test — libucimf 2.3.8 (OHOS aarch64, headless).
 *
 * Upstream ships no test suite, and its sample programs (sample/term/*.cpp)
 * call ucimf_init(), which NULL-derefs when fontconfig discovers no fonts
 * (Font::instance() returns NULL -> ->height() crash) and normally needs a
 * framebuffer. This test exercises the deterministic headless consumer
 * workflow instead:
 *
 *   1. ucimf_process_raw(): feed one raw console keycode event
 *      (KEY_LEFTCTRL = 29 from <linux/keyboard.h>). This drives the real
 *      keycode -> keysym -> terminal-string pipeline inside libucimf. In a
 *      pipe/CI environment the KDGKBENT/KDGKBSENT ioctls fail gracefully
 *      with ENOTTY, so keycode_to_keysym() returns K_HOLE and the Ctrl
 *      keypress path consumes the event: the function must return the same
 *      buffer pointer with length zeroed and the buffer cleared (upstream
 *      contract: modifier keys are swallowed, never forwarded to the app).
 *
 *   2. ucimf_switch(): with a payload that is not the 5-byte F11/F12
 *      escape sequence (ESC [ <digit> ~), the switch handler must pass
 *      through without touching the buffer (early-return contract) —
 *      proves the installed library exports and correctly executes the
 *      C entry points declared in <ucimf.h>.
 *
 * Both calls only touch code paths that never dereference the display
 * singletons (cwm/imf), so the test is crash-free headless — audited
 * against src/ucimf.cpp lines 326-420 (process_raw Ctrl path) and
 * 255-302 (switch early return), see notes.md.
 */
#include <errno.h>
#include <linux/input.h> /* KEY_LEFTCTRL */
#include <stdio.h>
#include <string.h>

#include <ucimf.h>

#ifndef KEY_LEFTCTRL
#define KEY_LEFTCTRL 29 /* <linux/input.h> event code for the left Ctrl key */
#endif

static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (cond) {                                                          \
            printf("PASS: %s\n", (msg));                                     \
        } else {                                                             \
            printf("FAIL: %s\n", (msg));                                     \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int main(void)
{
    /* --- 1. process_raw: Ctrl keypress event is consumed --------------- */
    char buf[16];
    int len = 1;
    buf[0] = (char)KEY_LEFTCTRL; /* 29 */

    char *ret = ucimf_process_raw(buf, &len);

    CHECK(ret == buf, "ucimf_process_raw returns the caller buffer");
    CHECK(len == 0, "ucimf_process_raw zeroes the length for a consumed "
                    "modifier keypress event");
    CHECK(buf[0] == '\0', "ucimf_process_raw clears the buffer for a "
                          "consumed modifier keypress event");

    /* --- 2. process_raw: release event is swallowed --------------------- */
    len = 1;
    buf[0] = (char)(KEY_LEFTCTRL | 0x80); /* high bit = release */
    ret = ucimf_process_raw(buf, &len);
    CHECK(ret == buf && len == 0 && buf[0] == '\0',
          "ucimf_process_raw swallows a modifier key release event");

    /* --- 3. ucimf_switch: non-escape payload passes through ------------ */
    unsigned char sw[5] = {'h', 'e', 'l', 'l', 'o'};
    int sw_len = 5;
    ucimf_switch(sw, &sw_len);
    CHECK(sw_len == 5 && memcmp(sw, "hello", 5) == 0,
          "ucimf_switch leaves a non-escape-sequence payload untouched");

    /* --- 4. ucimf_switch: wrong length passes through ------------------- */
    unsigned char esc[5] = {27, '[', '5', '0', '~'}; /* F12-like, len 4 */
    int esc_len = 4;
    ucimf_switch(esc, &esc_len);
    CHECK(esc_len == 4 && esc[0] == 27 && esc[4] == '~',
          "ucimf_switch leaves a wrong-length escape payload untouched");

    printf("%s: %d failure(s)\n", failures ? "FAILED" : "OK", failures);
    return failures ? 1 : 0;
}
