/* gen_wav.c — generate a short stereo 44.1 kHz PCM WAV for the round-trip
 * test (44-byte canonical header + sine samples). No dependencies. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SAMPLE_RATE 44100u
#define DURATION 0.25 /* seconds */

static void put_u32(FILE *f, unsigned v) {
    fputc(v & 0xFF, f);
    fputc((v >> 8) & 0xFF, f);
    fputc((v >> 16) & 0xFF, f);
    fputc((v >> 24) & 0xFF, f);
}
static void put_u16(FILE *f, unsigned v) {
    fputc(v & 0xFF, f);
    fputc((v >> 8) & 0xFF, f);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <out.wav>\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "wb");
    if (!f) {
        perror("fopen");
        return 1;
    }
    unsigned n = (unsigned)(SAMPLE_RATE * DURATION);
    unsigned data_len = n * 2 * 2; /* stereo, 16-bit */
    unsigned char *pcm = (unsigned char *)malloc(data_len);
    if (!pcm) {
        fclose(f);
        return 1;
    }
    for (unsigned i = 0; i < n; i++) {
        double s = 20000.0 * sin(2.0 * 3.14159265358979323846 * 440.0 *
                                 (double)i / (double)SAMPLE_RATE);
        short v = (short)s;
        /* little-endian L, R (same tone) */
        pcm[4 * i + 0] = (unsigned char)(v & 0xFF);
        pcm[4 * i + 1] = (unsigned char)((v >> 8) & 0xFF);
        pcm[4 * i + 2] = (unsigned char)(v & 0xFF);
        pcm[4 * i + 3] = (unsigned char)((v >> 8) & 0xFF);
    }

    fwrite("RIFF", 1, 4, f);
    put_u32(f, 36 + data_len);
    fwrite("WAVEfmt ", 1, 8, f);
    put_u32(f, 16);          /* fmt chunk size */
    put_u16(f, 1);           /* PCM */
    put_u16(f, 2);           /* channels */
    put_u32(f, SAMPLE_RATE); /* sample rate */
    put_u32(f, SAMPLE_RATE * 4);
    put_u16(f, 4); /* block align */
    put_u16(f, 16);
    fwrite("data", 1, 4, f);
    put_u32(f, data_len);
    fwrite(pcm, 1, data_len, f);
    fclose(f);
    free(pcm);
    printf("WAV generated: %u samples\n", n);
    return 0;
}
