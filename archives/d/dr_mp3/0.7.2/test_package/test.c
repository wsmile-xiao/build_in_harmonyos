/* test_dr_mp3 — consumer-level functional test for dr_mp3/0.7.2 (R34).
 *
 * Decodes a real MPEG1 Layer III frame (128 kbps CBR, 44.1 kHz, stereo)
 * through both the low-level (drmp3dec_*) and high-level (drmp3_*) APIs
 * and asserts that the decoded metadata round-trips.
 *
 * The frame is constructed in source (no external testvector needed):
 *   4-byte sync header  0xFF 0xFB 0x90 0x64
 *                        = sync | MPEG1 | Layer III | no CRC
 *                        | 128 kbps | 44100 Hz | no padding
 *                        | stereo | original | no emphasis
 *   22-byte side info   all-zero stereo side info (main_data_begin=0,
 *                        all part2_3_length/big_values zero => silent frame)
 *   391 bytes main data zeros
 * Frame size = 144 * 128000 / 44100 = 417 bytes.
 */
#include <stdio.h>
#include <string.h>

#define DR_MP3_IMPLEMENTATION
#include "dr_mp3.h"

static int g_failures = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (cond) {                                               \
            printf("PASS: %s\n", (msg));                          \
        } else {                                                  \
            printf("FAIL: %s\n", (msg));                          \
            g_failures++;                                         \
        }                                                         \
    } while (0)

int main(void)
{
    unsigned char frame[417];
    memset(frame, 0, sizeof(frame));
    frame[0] = 0xFF;
    frame[1] = 0xFB;
    frame[2] = 0x90;
    frame[3] = 0x64;

    /* Version macro must match the adapted release. */
    CHECK(strcmp(DRMP3_VERSION_STRING, "0.7.2") == 0,
          "DRMP3_VERSION_STRING is 0.7.2");

    /* Low-level API: decode the single frame. */
    drmp3dec dec;
    drmp3dec_frame_info info;
    drmp3dec_init(&dec);
    float pcm[1152 * 2];
    int decoded = drmp3dec_decode_frame(&dec, frame, (int)sizeof(frame), pcm, &info);
    CHECK(decoded == 1152, "low-level decode returns 1152 samples");
    CHECK(info.channels == 2, "channels == 2 (stereo)");
    CHECK(info.sample_rate == 44100, "sample_rate == 44100");
    CHECK(info.layer == 3, "layer == 3 (Layer III)");
    CHECK(info.bitrate_kbps == 128, "bitrate == 128 kbps");
    CHECK(info.frame_bytes == 417, "frame_bytes == 417");

    /* High-level API: full in-memory decode. */
    drmp3 mp3;
    drmp3_bool32 ok = drmp3_init_memory(&mp3, frame, sizeof(frame), NULL);
    CHECK(ok == DRMP3_TRUE, "drmp3_init_memory succeeds");
    CHECK(mp3.channels == 2, "high-level channels == 2");
    CHECK(mp3.sampleRate == 44100, "high-level sampleRate == 44100");
    float out[1152 * 2];
    drmp3_uint64 frames = drmp3_read_pcm_frames_f32(&mp3, 1152, out);
    CHECK(frames == 1152, "drmp3_read_pcm_frames_f32 returns 1152 frames");
    drmp3_uninit(&mp3);

    if (g_failures == 0) {
        printf("dr_mp3 test: all 11 assertions passed\n");
        return 0;
    }
    printf("dr_mp3 test: %d assertion(s) FAILED\n", g_failures);
    return 1;
}
