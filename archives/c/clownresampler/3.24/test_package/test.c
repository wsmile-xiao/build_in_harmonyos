#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "clownresampler.h"

/* Consumer test: use the public low-level API to resample a small
   mono buffer from 8000 Hz to 16000 Hz (2:1 upsampling) and verify
   that (a) Init succeeds, (b) output frames are produced, and
   (c) the produced output is finite and non-trivial. */

typedef struct
{
    cc_s32f *frames;
    size_t frame_count;
    size_t capacity;
} OutputCollector;

static cc_bool OutputCallback(void *user_data, const cc_s32f *frame, cc_u8f total_samples)
{
    OutputCollector *collector = (OutputCollector *)user_data;
    cc_u8f i;

    if (collector->frame_count >= collector->capacity)
        return cc_false;

    for (i = 0; i < total_samples; ++i)
        collector->frames[collector->frame_count * total_samples + i] = frame[i];

    collector->frame_count += 1;
    return cc_true;
}

int main(void)
{
    ClownResampler_LowLevel_State resampler;
    ClownResampler_Precomputed precomputed;
    const cc_u8f channels = 1;
    const cc_u32f input_sample_rate = 8000;
    const cc_u32f output_sample_rate = 16000;
    const size_t input_frames_total = 100;
    const size_t padding = 16; /* kernel radius padding */
    cc_s16l input_buffer[(input_frames_total + padding * 2)];
    size_t input_frames_remaining;
    OutputCollector collector;
    size_t i;
    cc_bool ok;

    /* Pre-compute the resampler state (public API). */
    ClownResampler_Precompute(&precomputed);

    if (!ClownResampler_LowLevel_Init(&resampler, channels, input_sample_rate, output_sample_rate, 16000))
    {
        fprintf(stderr, "FAIL: ClownResampler_LowLevel_Init failed\n");
        return 1;
    }

    /* Input: deterministic alternating impulses (mono, 16-bit). */
    memset(input_buffer, 0, sizeof(input_buffer));
    for (i = 0; i < input_frames_total; ++i)
        input_buffer[padding + i] = (cc_s16l)((i % 10 == 0) ? 4000 : 0);

    input_frames_remaining = input_frames_total;

    collector.frames = (cc_s32f *)calloc(input_frames_total * 4 * channels, sizeof(cc_s32f));
    collector.frame_count = 0;
    collector.capacity = input_frames_total * 4;

    ok = ClownResampler_LowLevel_Resample(&resampler, &precomputed,
                                          input_buffer, &input_frames_remaining,
                                          OutputCallback, &collector);

    if (collector.frame_count == 0)
    {
        fprintf(stderr, "FAIL: no output frames produced\n");
        free(collector.frames);
        return 1;
    }

    printf("clownresampler consumer test: %zu input frames -> %zu output frames (ok=%d)\n",
           input_frames_total, collector.frame_count, (int)ok);
    free(collector.frames);
    return 0;
}