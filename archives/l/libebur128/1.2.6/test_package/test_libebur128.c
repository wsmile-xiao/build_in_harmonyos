/* Consumer smoke test for the packaged libebur128 1.2.6.
 *
 * Compiles against the installed public header (ebur128.h) and links
 * the packaged library. Network-free, file-free and deterministic:
 * version query, init/channel-map/destroy lifecycle, silence handling
 * for short/float/double frame APIs, a sine-wave gated loudness check
 * with a wide tolerance, parameter changes, LRA / sample-peak /
 * relative-threshold queries, window/history setters, and two parallel
 * instances running independently.
 */
#include "ebur128.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    printf("%s - %s\n", cond ? "ok" : "FAIL", what);
    if (!cond)
        failures++;
}

#define SR 48000.0

/* Fill interleaved stereo float buffer with a 1 kHz sine at amplitude. */
static void fill_sine(float *buf, size_t frames, double amplitude)
{
    size_t i;
    for (i = 0; i < frames; ++i) {
        double v = amplitude * sin(2.0 * 3.141592653589793 * 1000.0 * (double)i / SR);
        buf[2 * i] = (float)v;
        buf[2 * i + 1] = (float)v;
    }
}

int main(void)
{
    int major = 0, minor = 0, patch = 0;

    /* 1: version query — header macros and runtime value must be 1.2.6. */
    ebur128_get_version(&major, &minor, &patch);
    check(major == EBUR128_VERSION_MAJOR && minor == EBUR128_VERSION_MINOR
              && patch == EBUR128_VERSION_PATCH && major == 1 && minor == 2 && patch == 6,
          "ebur128_get_version reports 1.2.6");

    /* 2: init / channel map / destroy lifecycle (stereo, mode I). */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_I);
        check(st != NULL && ebur128_set_channel(st, 0, EBUR128_LEFT) == EBUR128_SUCCESS
                  && ebur128_set_channel(st, 1, EBUR128_RIGHT) == EBUR128_SUCCESS,
              "init stereo + set LEFT/RIGHT channel map");
        ebur128_destroy(&st);
        check(st == NULL, "destroy clears the state pointer");
    }

    /* 3: short-frame silence keeps shortterm loudness at -inf. */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_S);
        short silence[4800 * 2];
        double out = 123.0;
        memset(silence, 0, sizeof(silence));
        ebur128_add_frames_short(st, silence, 4800);
        check(ebur128_loudness_shortterm(st, &out) == EBUR128_SUCCESS && out <= -70.0,
              "short-frame silence -> shortterm loudness -inf");
        ebur128_destroy(&st);
    }

    /* 4: float frames: 1 s of 1 kHz sine at 0.5 amplitude gives a finite
     * gated global loudness in a sane range (deterministic wide window:
     * about -12 LUFS, asserted within (-30, 0)). */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_I);
        float *buf = (float *)malloc(48000 * 2 * sizeof(float));
        double out = 0.0;
        fill_sine(buf, 48000, 0.5);
        ebur128_add_frames_float(st, buf, 48000);
        check(ebur128_loudness_global(st, &out) == EBUR128_SUCCESS
                  && out == out && out > -30.0 && out < 0.0,
              "float 1 kHz sine -> gated global loudness in (-30, 0) LUFS");
        /* 5: relative threshold from the same state is finite (or -inf
         * before gating fills in) and the query succeeds. */
        {
            double thr = 0.0;
            check(ebur128_relative_threshold(st, &thr) == EBUR128_SUCCESS
                      && (thr == thr || thr <= -70.0),
                  "relative_threshold query succeeds with a sane value");
        }
        ebur128_destroy(&st);
        free(buf);
    }

    /* 6: double frames + sample peak tracks the input amplitude. */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_I | EBUR128_MODE_SAMPLE_PEAK);
        double *buf = (double *)malloc(4800 * 2 * sizeof(double));
        double peak = 0.0;
        size_t i;
        /* Generate the sine directly in double precision (an in-place
         * float->double rewrite would trample not-yet-read samples). */
        for (i = 0; i < 4800 * 2; ++i)
            buf[i] = 0.8 * sin(2.0 * 3.141592653589793 * 1000.0 * (double)(i / 2) / SR);
        ebur128_add_frames_double(st, buf, 4800);
        check(ebur128_sample_peak(st, 0, &peak) == EBUR128_SUCCESS
                  && peak > 0.799 && peak < 0.801,
              "sample_peak tracks 0.8 amplitude input");
        ebur128_destroy(&st);
        free(buf);
    }

    /* 7: change_parameters to mono 44100 Hz succeeds on a fresh state. */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_I);
        check(ebur128_change_parameters(st, 1, 44100) == EBUR128_SUCCESS,
              "change_parameters to 1ch/44100Hz succeeds");
        ebur128_destroy(&st);
    }

    /* 8: loudness_range (LRA) query succeeds; silence yields 0 LU. */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_LRA);
        double lra = -1.0;
        double *buf = (double *)malloc(48000 * 2 * sizeof(double));
        memset(buf, 0, 48000 * 2 * sizeof(double));
        ebur128_add_frames_double(st, buf, 48000);
        check(ebur128_loudness_range(st, &lra) == EBUR128_SUCCESS && lra >= 0.0 && lra < 1.0,
              "loudness_range on 1 s silence is 0 LU");
        ebur128_destroy(&st);
        free(buf);
    }

    /* 9: window / history setters accept documented values (mode I). */
    {
        ebur128_state *st = ebur128_init(2, 48000, EBUR128_MODE_I);
        check(ebur128_set_max_window(st, 4000) == EBUR128_SUCCESS
                  && ebur128_set_max_history(st, 3000) == EBUR128_SUCCESS,
              "set_max_window/set_max_history succeed");
        ebur128_destroy(&st);
    }

    /* 10: two instances process different amplitudes independently. */
    {
        ebur128_state *st1 = ebur128_init(2, 48000, EBUR128_MODE_I);
        ebur128_state *st2 = ebur128_init(2, 48000, EBUR128_MODE_I);
        float *buf1 = (float *)malloc(48000 * 2 * sizeof(float));
        float *buf2 = (float *)malloc(48000 * 2 * sizeof(float));
        double l1 = 0.0, l2 = 0.0;
        fill_sine(buf1, 48000, 0.5);
        fill_sine(buf2, 48000, 0.25);
        ebur128_add_frames_float(st1, buf1, 48000);
        ebur128_add_frames_float(st2, buf2, 48000);
        ebur128_loudness_global(st1, &l1);
        ebur128_loudness_global(st2, &l2);
        check(l1 == l1 && l2 == l2 && l1 > l2 && (l1 - l2) > 3.0 && (l1 - l2) < 9.0,
              "parallel instances independent (~6 LU apart for 2x amplitude)");
        ebur128_destroy(&st1);
        ebur128_destroy(&st2);
        free(buf1);
        free(buf2);
    }

    if (failures != 0) {
        printf("%d check(s) FAILED\n", failures);
        return 1;
    }
    printf("all 11 checks passed\n");
    return 0;
}
