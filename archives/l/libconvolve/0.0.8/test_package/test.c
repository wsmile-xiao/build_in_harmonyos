#include <convolve.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static int check_wav_load(void) {
    static const unsigned char wav[] = {
        'R','I','F','F', 52,0,0,0, 'W','A','V','E',
        'f','m','t',' ', 16,0,0,0, 1,0, 1,0,
        0x40,0x1f,0,0, 0x80,0x3e,0,0, 2,0, 16,0,
        'd','a','t','a', 16,0,0,0,
        0xff,0x7f, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0
    };
    const char *filename = "libconvolve-test-response.wav";
    response_t response = {0};
    FILE *file = fopen(filename, "wb");
    if (!file) {
        fputs("failed to create test WAV\n", stderr);
        return 0;
    }
    size_t written = fwrite(wav, 1, sizeof(wav), file);
    int closed = fclose(file);
    if (written != sizeof(wav) || closed != 0) {
        fputs("failed to write test WAV\n", stderr);
        remove(filename);
        return 0;
    }
    if (!load_response(&response, (char *)filename, 8000)) {
        fputs("load_response failed\n", stderr);
        remove(filename);
        return 0;
    }
    remove(filename);
    int ok = response.channels == 1 && response.length == 8 &&
             response.channel_data && response.channel_data[0] &&
             response.channel_data[0][0] > 0.9f;
    if (!ok) {
        fputs("unexpected decoded WAV response\n", stderr);
    }
    if (response.channel_data) {
        for (int i = 0; i < response.channels; ++i) {
            free(response.channel_data[i]);
        }
        free(response.channel_data);
    }
    return ok;
}

int main(void) {
    float impulse[] = {1.0f};
    float *response_channels[] = {impulse};
    response_t response = {1, 1, response_channels};
    response_t *responses[] = {&response};
    convolution_t convolution = {0};
    float input[8] = {1.0f};
    float output[8] = {0};
    float *inputs[] = {input};
    float *outputs[] = {output};

    libconvolve_init();
    if (!convolution_init(&convolution, 1, 1, responses, 8, 0)) {
        fputs("convolution_init failed\n", stderr);
        return 1;
    }
    if (!convolution_process(&convolution, inputs, outputs, 1.0f, -1, -1)) {
        fputs("convolution_process failed\n", stderr);
        convolution_destroy(&convolution);
        return 1;
    }
    if (!isfinite(output[0]) || output[0] <= 0.0f) {
        fprintf(stderr, "invalid impulse response: %f\n", output[0]);
        convolution_destroy(&convolution);
        return 1;
    }
    for (int i = 1; i < 8; ++i) {
        if (!isfinite(output[i]) || fabsf(output[i]) > 0.001f) {
            fprintf(stderr, "unexpected impulse tail at %d: %f\n", i, output[i]);
            convolution_destroy(&convolution);
            return 1;
        }
    }
    if (!convolution_destroy(&convolution)) {
        fputs("convolution_destroy failed\n", stderr);
        return 1;
    }
    if (!check_wav_load()) {
        return 1;
    }
    printf("libconvolve impulse and WAV-load tests passed (sample=%f)\n", output[0]);
    return 0;
}
