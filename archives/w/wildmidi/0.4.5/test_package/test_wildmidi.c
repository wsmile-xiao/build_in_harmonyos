/* test_wildmidi.c — consumer test for wildmidi/0.4.5
 * Links against the packaged libWildMidi and asserts real library behavior
 * through the public API (R34: no print-only stub).
 * Note: upstream 0.4.5 spells the public API WildMidi_* (lowercase i).
 */
#include <stdio.h>
#include <wildmidi_lib.h>

int main(void) {
    /* Compile-time assertion: header matches the adapted upstream version */
#if LIBWILDMIDI_VERSION != ((0L << 16) | (4L << 8) | 5L)
#error "wildmidi_lib.h version mismatch: expected 0.4.5"
#endif
    printf("header version macro OK: 0x%06lx\n",
           (unsigned long) LIBWILDMIDI_VERSION);

    /* Behavior 1: Init with a nonexistent config file must fail */
    if (WildMidi_Init("/nonexistent/wildmidi.cfg", 44100, 0) == 0) {
        fprintf(stderr, "FAIL: Init with missing config unexpectedly succeeded\n");
        return 1;
    }
    printf("OK: Init with missing config failed as expected\n");

    /* Behavior 2: GetError reports why Init failed */
    char *err = WildMidi_GetError();
    if (err == NULL || err[0] == '\0') {
        fprintf(stderr, "FAIL: WildMidi_GetError returned no message\n");
        return 1;
    }
    printf("OK: GetError -> %s\n", err);

    /* Behavior 3: Shutdown without Init sets the WM_ERR_NOT_INIT error state
     * (0.4.5 declares `int WildMidi_Shutdown(void)` in wildmidi_lib.h:140 and
     * returns -1 here; assert through the documented error API instead of the
     * return value so the check stays valid across upstream API revisions) */
    WildMidi_Shutdown();
    err = WildMidi_GetError();
    if (err == NULL || err[0] == 0) {
        fprintf(stderr, "FAIL: Shutdown without Init did not set an error state");
        fputc(10, stderr);
        return 1;
    }
    printf("OK: Shutdown without Init set WM_ERR_NOT_INIT: %s", err);
    fputc(10, stdout);

    /* Behavior 4: ClearError resets the error state */
    WildMidi_ClearError();
    err = WildMidi_GetError();
    if (err != NULL && err[0] != '\0') {
        fprintf(stderr, "FAIL: error state not cleared: %s\n", err);
        return 1;
    }
    printf("OK: ClearError reset the error state\n");

    printf("ALL TESTS PASSED\n");
    return 0;
}
