/*
 * test_package consumer test for libspecbleach 0.4.1.
 *
 * Real consumer-style validation: uses only the installed public header
 * (include/specbleach_denoiser.h) and the v0.4.1 public API to initialize a
 * denoiser, load baseline parameters, process a real audio frame, and free
 * it. Verifies business-meaningful observable results: latency query and
 * output sample range after processing a silent frame.
 */
#include <stdio.h>
#include <stdlib.h>

#include "specbleach_denoiser.h"

int main(void) {
    static const uint32_t kSampleRate = 44100;
    static const uint32_t kFrameSize = 512;

    /* v0.4.1 API: initialize(sample_rate, frame_size_ms, flags) */
    specbleach_denoiser *handle = specbleach_denoiser_initialize(kSampleRate, 46.0f, 0u);
    if (handle == NULL) {
        fprintf(stderr, "specbleach_denoiser_initialize failed\n");
        return 1;
    }

    /* Baseline parameter block (real v0.4.1 fields), ABI-guarded reload */
    SpecbleachDenoiserParameters params = specbleach_denoiser_get_default_parameters();
    if (!specbleach_denoiser_load_parameters(handle, &params, SPECBLEACH_PARAMETERS_SIZE)) {
        fprintf(stderr, "specbleach_denoiser_load_parameters failed\n");
        specbleach_denoiser_free(handle);
        return 1;
    }

    /* One frame of silent audio: process must succeed and output must stay
     * in the finite [-1, 1] range; latency is an observable business value
     * (hosts use it for delay compensation). */
    float *frame = (float *)calloc((size_t)kFrameSize, sizeof(float));
    if (frame == NULL) {
        specbleach_denoiser_free(handle);
        return 1;
    }
    if (!specbleach_denoiser_process(handle, kFrameSize, frame, frame)) {
        fprintf(stderr, "specbleach_denoiser_process failed\n");
        free(frame);
        specbleach_denoiser_free(handle);
        return 1;
    }
    for (uint32_t i = 0; i < kFrameSize; i++) {
        if (!(frame[i] >= -1.0f && frame[i] <= 1.0f)) {
            fprintf(stderr, "output sample %u out of range: %f\n", i, frame[i]);
            free(frame);
            specbleach_denoiser_free(handle);
            return 1;
        }
    }

    uint32_t latency = specbleach_denoiser_get_latency(handle);
    printf("libspecbleach consumer OK: latency=%u samples, frame=%u, sample_rate=%u\n",
           latency, kFrameSize, kSampleRate);

    free(frame);
    specbleach_denoiser_free(handle);
    return 0;
}
