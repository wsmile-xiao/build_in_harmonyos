#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rnnoise.h"

int main(void) {
    int size = rnnoise_get_size();
    int frame_size = rnnoise_get_frame_size();
    if (size <= 0 || frame_size <= 0) {
        fprintf(stderr, "invalid rnnoise sizes: size=%d frame_size=%d\n",
                size, frame_size);
        return 1;
    }

    DenoiseState *st = rnnoise_create(NULL);
    if (!st) {
        fprintf(stderr, "rnnoise_create failed\n");
        return 2;
    }

    float *frame = (float *)calloc((size_t)frame_size, sizeof(float));
    if (!frame) {
        fprintf(stderr, "frame alloc failed\n");
        rnnoise_destroy(st);
        return 3;
    }

    int ret = rnnoise_process_frame(st, frame, frame);
    if (ret != 0) {
        fprintf(stderr, "rnnoise_process_frame returned %d\n", ret);
        free(frame);
        rnnoise_destroy(st);
        return 4;
    }

    free(frame);
    rnnoise_destroy(st);
    printf("rnnoise API assertions: sizes/create/process/destroy passed\n");
    return 0;
}
