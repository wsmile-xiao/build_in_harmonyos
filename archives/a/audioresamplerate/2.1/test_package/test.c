/*
** test_audioresamplerate — Conan L1 consumer-style test.
**
** Uses only the public API from the installed package header
** samplerate.h (Secret Rabbit Code API): src_simple() performs a real
** sample-rate conversion of an audio buffer and returns a verifiable
** number of output frames.
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "samplerate.h"

#define INPUT_FRAMES 1600   /* 0.1s @ 16 kHz */

int main(void)
{
    SRC_DATA data;
    float *in, *out;
    long expect_out;
    const char *ver;

    ver = src_get_version();
    if (ver == NULL || ver[0] == '\0')
    {
        fprintf(stderr, "FAIL: src_get_version() returned empty\n");
        return 1;
    }
    printf("libsamplerate version: %s\n", ver);

    in = (float *)calloc(INPUT_FRAMES, sizeof(float));
    out = (float *)calloc((size_t)INPUT_FRAMES * 3, sizeof(float));
    if (in == NULL || out == NULL)
    {
        fprintf(stderr, "FAIL: calloc\n");
        return 1;
    }

    /* 16 kHz -> 48 kHz mono test tone (44100/16 = 2756.25 Hz pattern:
       discrete ramp, energy at many bins), amplitude 0.5 */
    for (long i = 0; i < INPUT_FRAMES; i++)
        in[i] = 0.5f * ((float)(i % 25) / 25.0f - 0.5f);

    memset(&data, 0, sizeof(data));
    data.data_in = in;
    data.data_out = out;
    data.input_frames = INPUT_FRAMES;
    data.output_frames = INPUT_FRAMES * 3;
    data.src_ratio = 3.0;               /* 16k -> 48k */
    data.end_of_input = 1;

    if (src_simple(&data, SRC_SINC_FASTEST, 1) != 0)
    {
        fprintf(stderr, "FAIL: src_simple returned error: %s\n",
                src_strerror(src_error(NULL)));
        return 1;
    }

    expect_out = (long)(INPUT_FRAMES * data.src_ratio);
    printf("input_frames=%ld used=%ld output_frames_used=%ld generated=%ld (expect ~%ld)\n",
           data.input_frames, data.input_frames_used,
           data.output_frames, data.output_frames_gen, expect_out);

    if (data.output_frames_gen <= 0)
    {
        fprintf(stderr, "FAIL: no output frames generated\n");
        return 1;
    }
    if (data.output_frames_gen < expect_out / 2 || data.output_frames_gen > expect_out * 2)
    {
        fprintf(stderr, "FAIL: output frame count %ld out of sane range of ~%ld\n",
                data.output_frames_gen, expect_out);
        return 1;
    }

    /* Output must contain non-zero samples (real conversion happened). */
    int nonzero = 0;
    for (long i = 0; i < data.output_frames_gen; i++)
        if (out[i] != 0.0f)
        {
            nonzero = 1;
            break;
        }
    if (!nonzero)
    {
        fprintf(stderr, "FAIL: output buffer all zeros\n");
        return 1;
    }

    free(in);
    free(out);
    printf("test audioresamplerate 2.1: PASS\n");
    return 0;
}
