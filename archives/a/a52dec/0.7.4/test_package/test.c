#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "a52.h"

int main(void) {
    a52_state_t *state = a52_init(0);
    if (!state) {
        fprintf(stderr, "a52_init failed\n");
        return 1;
    }

    uint8_t header[8] = {0x0b, 0x77, 0, 0, 0, 0, 0x40, 0};
    int flags = 0;
    int sample_rate = 0;
    int bit_rate = 0;
    if (a52_syncinfo(header, &flags, &sample_rate, &bit_rate) != 128) {
        fprintf(stderr, "valid AC-3 header was not parsed\n");
        a52_free(state);
        return 2;
    }
    if (sample_rate != 48000 || bit_rate != 32000) {
        fprintf(stderr, "unexpected stream info: rate=%d bitrate=%d\n", sample_rate, bit_rate);
        a52_free(state);
        return 3;
    }

    header[0] = 0;
    if (a52_syncinfo(header, &flags, &sample_rate, &bit_rate) != 0) {
        fprintf(stderr, "invalid sync word was accepted\n");
        a52_free(state);
        return 4;
    }

    a52_free(state);
    puts("a52 API assertions: 3 passed");
    return 0;
}
