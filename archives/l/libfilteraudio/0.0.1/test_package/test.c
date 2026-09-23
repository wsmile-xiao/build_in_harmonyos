/* libfilteraudio consumer / adaptation test (HarmonyOS PC aarch64).
 *
 * Links the installed libfilteraudio and drives the public API from
 * filter_audio.h: handle lifecycle, argument contracts, multi-rate frame
 * processing, VAD decision on digital silence, and real signal modification
 * by the filter chain (echo/NS/AGC/ZAM). Exits non-zero on any failure.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "filter_audio.h"

#define FS 48000u
#define FRAME (FS / 100u) /* 480 samples = 10 ms at 48 kHz */

static int g_checks;
static int g_failed;

#define CHECK(cond, msg)                                    \
    do {                                                    \
        g_checks++;                                         \
        if (cond) {                                         \
            printf("ok   - %s\n", (msg));                   \
        } else {                                            \
            g_failed++;                                     \
            printf("FAIL - %s\n", (msg));                   \
        }                                                   \
    } while (0)

static void fill_tone(int16_t *buf, unsigned n, double freq, double amp, double phase0)
{
    unsigned i;
    for (i = 0; i < n; i++) {
        buf[i] = (int16_t)(amp * sin(2.0 * 3.14159265358979323846 * freq * ((double)i / (double)FS) + phase0));
    }
}

static double rms(const int16_t *buf, unsigned n)
{
    double acc = 0.0;
    unsigned i;
    for (i = 0; i < n; i++) {
        acc += (double)buf[i] * (double)buf[i];
    }
    return sqrt(acc / (double)n);
}

int main(void)
{
    int16_t frame[FRAME];
    int16_t tone_in[FRAME];
    int16_t echo_in[FRAME];
    Filter_Audio *fa;
    int i;
    int rc;
    int saw_silence_voice = 0;
    double in_rms, out_rms;

    memset(frame, 0, sizeof(frame));

    /* ---- argument contracts ---- */
    CHECK(new_filter_audio(0) == NULL, "new_filter_audio(0) returns NULL");
    CHECK(filter_audio(NULL, frame, FRAME) == -1, "filter_audio(NULL, ...) returns -1");
    CHECK(pass_audio_output(NULL, frame, FRAME) == -1, "pass_audio_output(NULL, ...) returns -1");
    CHECK(set_echo_delay_ms(NULL, 50) == -1, "set_echo_delay_ms(NULL, ...) returns -1");
    CHECK(enable_disable_filters(NULL, 1, 1, 1, 1) == -1, "enable_disable_filters(NULL, ...) returns -1");

    /* ---- handle lifecycle at 48 kHz ---- */
    fa = new_filter_audio(FS);
    CHECK(fa != NULL, "new_filter_audio(48000) returns a handle");

    CHECK(set_echo_delay_ms(fa, 60) == 0, "set_echo_delay_ms(60) succeeds");
    CHECK(enable_disable_filters(fa, 1, 1, 1, 1) == 0, "enable_disable_filters(1,1,1,1) succeeds");
    CHECK(filter_audio(fa, frame, FRAME + 1) == -1,
          "filter_audio() rejects a frame that is not a multiple of fs/100");
    CHECK(pass_audio_output(fa, frame, FRAME + 1) == -1,
          "pass_audio_output() rejects a frame that is not a multiple of fs/100");

    /* ---- VAD disabled: frame is always reported as processed ---- */
    CHECK(enable_disable_filters(fa, 1, 1, 1, 0) == 0, "disable VAD");
    CHECK(filter_audio(fa, frame, FRAME) == 1,
          "filter_audio() reports success on a 10 ms frame with VAD disabled");

    /* ---- VAD enabled: digital silence must not be reported as voice ---- */
    CHECK(enable_disable_filters(fa, 1, 1, 1, 1) == 0, "re-enable VAD");
    for (i = 0; i < 50; i++) {
        memset(frame, 0, sizeof(frame));
        rc = filter_audio(fa, frame, FRAME);
        if (rc == -1) {
            break;
        }
        if (rc == 1) {
            saw_silence_voice = 1;
        }
    }
    CHECK(rc != -1, "filter_audio() never fails over 50 silence frames");
    CHECK(saw_silence_voice == 0, "VAD reports no voice for digital silence");

    /* ---- a real tone is classified as voice and is actually filtered ---- */
    fill_tone(tone_in, FRAME, 440.0, 8000.0, 0.0);
    memcpy(frame, tone_in, sizeof(frame));
    rc = filter_audio(fa, frame, FRAME);
    CHECK(rc == 1, "VAD reports voice for a 440 Hz tone");
    CHECK(memcmp(frame, tone_in, sizeof(frame)) != 0,
          "filter chain modifies the near-end buffer (not a stub)");

    /* ---- echo canceller reduces the level of the far-end echo ---- */
    {
        Filter_Audio *fa2 = new_filter_audio(FS);
        int16_t far[FRAME];
        double out_acc = 0.0;
        CHECK(fa2 != NULL, "second handle for the echo-cancellation scenario");
        if (fa2 != NULL) {
            CHECK(set_echo_delay_ms(fa2, 50) == 0, "set_echo_delay_ms(50) on the second handle");
            CHECK(enable_disable_filters(fa2, 1, 1, 1, 1) == 0, "enable all filters on the second handle");
            in_rms = 0.0;
            for (i = 0; i < 200; i++) {
                fill_tone(far, FRAME, 440.0, 8000.0, 0.0);
                memcpy(echo_in, far, sizeof(echo_in));
                rc = pass_audio_output(fa2, far, FRAME);
                if (rc != 0) {
                    break;
                }
                rc = filter_audio(fa2, echo_in, FRAME);
                if (rc == -1) {
                    break;
                }
                if (i >= 150) { /* measure after the canceller has converged */
                    in_rms += rms(far, FRAME);
                    out_acc += rms(echo_in, FRAME);
                }
            }
            in_rms /= 50.0;
            out_rms = out_acc / 50.0;
            CHECK(rc != -1, "echo-cancellation scenario runs 200 frames without error");
            printf("     far-end RMS %.1f -> near-end RMS %.1f (ratio %.3f)\n",
                   in_rms, out_rms, in_rms > 0.0 ? out_rms / in_rms : -1.0);
            CHECK(in_rms > 0.0 && out_rms < in_rms,
                  "echo canceller attenuates the far-end echo");
            kill_filter_audio(fa2);
        }
    }

    kill_filter_audio(fa);

    /* ---- the same API works at 8/16/32 kHz frames ---- */
    {
        static const uint32_t rates[] = {8000u, 16000u, 32000u};
        unsigned r;
        for (r = 0; r < sizeof(rates) / sizeof(rates[0]); r++) {
            Filter_Audio *fr = new_filter_audio(rates[r]);
            int16_t buf[320];
            unsigned n = rates[r] / 100u;
            char msg[96];
            CHECK(fr != NULL, "handle at alternate sample rate");
            if (fr == NULL) {
                continue;
            }
            fill_tone(buf, n, 440.0, 8000.0, 0.0);
            rc = filter_audio(fr, buf, n);
            snprintf(msg, sizeof(msg), "filter_audio() succeeds on a 10 ms %u Hz frame", rates[r]);
            CHECK(rc != -1, msg);
            kill_filter_audio(fr);
        }
    }

    kill_filter_audio(NULL); /* documented no-op on a NULL handle */

    printf("\n%d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
