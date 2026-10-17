#include <stdio.h>
#include <stdlib.h>
#include <speex/speex_resampler.h>

int main(void) {
    int err;
    SpeexResamplerState *st = speex_resampler_init(1, 44100, 48000, 4, &err);
    if (err != RESAMPLER_ERR_SUCCESS || st == NULL) {
        fprintf(stderr, "speex_resampler_init failed: %s\n", speex_resampler_strerror(err));
        return 1;
    }

    spx_int16_t in[256] = {0};
    spx_int16_t out[256];
    unsigned int in_len = 256;
    unsigned int out_len = 256;
    for (int i = 0; i < 256; i++) {
        in[i] = (spx_int16_t)(i * 100);
    }

    err = speex_resampler_process_int(st, 0, in, &in_len, out, &out_len);
    if (err != RESAMPLER_ERR_SUCCESS) {
        fprintf(stderr, "speex_resampler_process_int failed: %s\n", speex_resampler_strerror(err));
        speex_resampler_destroy(st);
        return 1;
    }

    if (out_len == 0) {
        fprintf(stderr, "speex_resampler produced no output\n");
        speex_resampler_destroy(st);
        return 1;
    }

    printf("speexdsp test: resampled %u -> %u samples OK\n", in_len, out_len);
    speex_resampler_destroy(st);
    return 0;
}
