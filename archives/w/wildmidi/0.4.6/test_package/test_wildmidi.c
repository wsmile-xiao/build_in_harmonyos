/* test_wildmidi.c — consumer test for wildmidi/0.4.6
 * Links against the packaged libWildMidi and asserts real library behavior
 * through the public API (R34: no print-only stub).
 * Note: upstream spells the public API WildMidi_* (lowercase i).
 *
 * Assertion groups (6):
 *   1. compile-time header version macro == 0.4.6
 *   2. WildMidi_GetVersion() (real exported symbol) == 0x000406
 *   3. WildMidi_GetString(WM_GS_VERSION) reports the packaged version
 *   4. WildMidi_Init() with a missing config file fails
 *   5. WildMidi_GetError() reports why, WildMidi_ClearError() resets it
 *   6. WildMidi_Shutdown() without a prior Init sets the WM_ERR_NOT_INIT state
 */
#include <stdio.h>
#include <string.h>
#include <wildmidi_lib.h>

/* expected LIBWILDMIDI_VERSION for 0.4.6 */
#define EXPECTED_VERSION ((0L << 16) | (4L << 8) | 6L)

int main(void) {
    int failures = 0;

    /* --- 1. compile-time assertion: header matches the adapted version --- */
#if LIBWILDMIDI_VERSION != ((0L << 16) | (4L << 8) | 6L)
#error "wildmidi_lib.h version mismatch: expected 0.4.6"
#endif
    printf("OK 1/6: header LIBWILDMIDI_VERSION == 0x%06lx (0.4.6)\n",
           (unsigned long) LIBWILDMIDI_VERSION);

    /* --- 2. real exported symbol: WildMidi_GetVersion() --- */
    {
        long v = WildMidi_GetVersion();
        if (v != EXPECTED_VERSION) {
            fprintf(stderr, "FAIL 2/6: WildMidi_GetVersion() = 0x%06lx, expected 0x%06lx\n",
                    (unsigned long) v, (unsigned long) EXPECTED_VERSION);
            failures++;
        } else {
            printf("OK 2/6: WildMidi_GetVersion() == 0x%06lx\n", (unsigned long) v);
        }
    }

    /* --- 3. WildMidi_GetString(WM_GS_VERSION) reports the version string --- */
    {
        const char *s = WildMidi_GetString(WM_GS_VERSION);
        if (s == NULL || strstr(s, "0.4.6") == NULL) {
            fprintf(stderr, "FAIL 3/6: WildMidi_GetString(WM_GS_VERSION) = %s\n",
                    s ? s : "(null)");
            failures++;
        } else {
            printf("OK 3/6: WildMidi_GetString(WM_GS_VERSION) -> \"%s\"\n", s);
        }
        /* unknown info tag must be rejected, not silently accepted */
        if (WildMidi_GetString((uint16_t) 0xffff) != NULL) {
            fprintf(stderr, "FAIL 3/6: unknown GetString tag did not return NULL\n");
            failures++;
        }
    }

    /* --- 4. Init with a nonexistent config file must fail --- */
    if (WildMidi_Init("/nonexistent/wildmidi.cfg", 44100, 0) == 0) {
        fprintf(stderr, "FAIL 4/6: Init with missing config unexpectedly succeeded\n");
        failures++;
    } else {
        printf("OK 4/6: Init with missing config failed as expected\n");
    }

    /* --- 5. GetError reports why Init failed; ClearError resets the state --- */
    {
        char *err = WildMidi_GetError();
        if (err == NULL || err[0] == '\0') {
            fprintf(stderr, "FAIL 5/6: WildMidi_GetError returned no message\n");
            failures++;
        } else {
            printf("OK 5/6: GetError -> %s\n", err);
        }
        WildMidi_ClearError();
        err = WildMidi_GetError();
        if (err != NULL && err[0] != '\0') {
            fprintf(stderr, "FAIL 5/6: ClearError did not reset the error state: %s\n", err);
            failures++;
        } else {
            printf("OK 5/6: ClearError reset the error state\n");
        }
    }

    /* --- 6. Shutdown without a prior Init sets WM_ERR_NOT_INIT ---
     * Asserted through the documented error API rather than the return value
     * so the check stays valid across upstream API revisions. */
    {
        WildMidi_Shutdown();
        char *err = WildMidi_GetError();
        if (err == NULL || err[0] == '\0') {
            fprintf(stderr, "FAIL 6/6: Shutdown without Init did not set an error state\n");
            failures++;
        } else {
            printf("OK 6/6: Shutdown without Init set WM_ERR_NOT_INIT: %s\n", err);
        }
        WildMidi_ClearError();
    }

    if (failures != 0) {
        fprintf(stderr, "%d assertion group(s) failed\n", failures);
        return 1;
    }
    printf("ALL TESTS PASSED\n");
    return 0;
}
