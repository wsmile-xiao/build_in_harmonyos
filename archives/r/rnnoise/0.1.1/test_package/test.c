#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rnnoise.h"

int main(void) {
    int sample_rate = 48000;
    DenoiseState *st = rnnoise_create(NULL);
    if (!st) {
        fprintf(stderr, "rnnoise_create failed\n");
        return 1;
    }

    /* 10 ms @ 48 kHz = 480 samples per frame (RNNoise frame size). */
    float frame[480];
    for (int i = 0; i < 480; i++) {
        frame[i] = 0.0f; /* silence frame */
    }

    int ret = rnnoise_process_frame(st, frame, frame);
    if (ret != 0) {
        fprintf(stderr, "rnnoise_process_frame returned %d\n", ret);
        rnnoise_destroy(st);
        return 2;
    }

    rnnoise_destroy(st);
    printf("rnnoise API assertions: create/process/destroy passed\n");
    return 0;
}
