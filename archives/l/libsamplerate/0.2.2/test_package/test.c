#include <stdio.h>
#include <stdlib.h>
#include <samplerate.h>

int main(void) {
    /* Test 1: Check version string */
    const char *ver = src_get_version();
    if (!ver || ver[0] == '\0') {
        fprintf(stderr, "FAIL: src_get_version() returned empty\n");
        return 1;
    }
    printf("src_get_version(): %s\n", ver);

    /* Test 2: Check converter name */
    const char *name = src_get_name(SRC_SINC_BEST_QUALITY);
    if (!name || name[0] == '\0') {
        fprintf(stderr, "FAIL: src_get_name() returned empty\n");
        return 1;
    }
    printf("src_get_name(SRC_SINC_BEST_QUALITY): %s\n", name);

    /* Test 3: Simple sample rate conversion */
    /* Convert 1 second of 44100Hz mono to 48000Hz */
    long input_frames = 100;
    long output_frames = 120;
    float *input = (float *)calloc(input_frames, sizeof(float));
    float *output = (float *)calloc(output_frames, sizeof(float));

    if (!input || !output) {
        fprintf(stderr, "FAIL: memory allocation failed\n");
        free(input);
        free(output);
        return 1;
    }

    /* Fill input with a simple sine-like pattern */
    for (long i = 0; i < input_frames; i++) {
        input[i] = (float)i / (float)input_frames;
    }

    SRC_DATA data;
    data.data_in = input;
    data.data_out = output;
    data.input_frames = input_frames;
    data.output_frames = output_frames;
    data.src_ratio = 1.2;  /* 44100 -> 48000 ratio approx */
    data.end_of_input = 1;

    int error = src_simple(&data, SRC_SINC_BEST_QUALITY, 1);
    if (error != 0) {
        fprintf(stderr, "FAIL: src_simple() error: %s\n", src_strerror(error));
        free(input);
        free(output);
        return 1;
    }

    printf("src_simple() succeeded: input_frames_used=%ld, output_frames_gen=%ld\n",
           data.input_frames_used, data.output_frames_gen);

    if (data.output_frames_gen <= 0) {
        fprintf(stderr, "FAIL: no output frames generated\n");
        free(input);
        free(output);
        return 1;
    }

    /* Test 4: Create and destroy a converter state */
    int err2;
    SRC_STATE *state = src_new(SRC_SINC_FASTEST, 1, &err2);
    if (!state) {
        fprintf(stderr, "FAIL: src_new() failed: %s\n", src_strerror(err2));
        free(input);
        free(output);
        return 1;
    }
    printf("src_new(SRC_SINC_FASTEST) succeeded\n");
    src_delete(state);

    free(input);
    free(output);
    printf("All tests passed!\n");
    return 0;
}
