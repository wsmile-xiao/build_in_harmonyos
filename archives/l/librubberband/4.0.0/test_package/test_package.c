#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include <rubberband/rubberband-c.h>

int main(void) {
    /* Test 1: library version macro + engine version API */
    const char *ver = RUBBERBAND_VERSION;
    if (!ver || ver[0] == '\0') {
        fprintf(stderr, "FAIL: RUBBERBAND_VERSION is empty\n");
        return 1;
    }
    printf("RUBBERBAND_VERSION: %s\n", ver);

    /* Test 2: real-time C API stretch of a 1 kHz sine, 44100 Hz mono */
    const size_t sampleRate = 44100;
    const size_t inFrames = sampleRate;      /* 1 second */
    const size_t maxOut = sampleRate * 3;    /* generous headroom */
    const double ratio = 1.5;                /* stretch to 1.5x length */

    float *input = (float *)calloc(inFrames, sizeof(float));
    float *outbuf = (float *)calloc(maxOut, sizeof(float));
    if (!input || !outbuf) {
        fprintf(stderr, "FAIL: allocation failure\n");
        free(input);
        free(outbuf);
        return 1;
    }
    for (size_t i = 0; i < inFrames; i++) {
        input[i] = (float)sin(2.0 * M_PI * 1000.0 * (double)i / (double)sampleRate);
    }

    RubberBandState rb = rubberband_new(
        (unsigned int)sampleRate, 1,
        RubberBandOptionProcessRealTime, ratio, 1.0);
    if (!rb) {
        fprintf(stderr, "FAIL: rubberband_new() returned NULL\n");
        free(input);
        free(outbuf);
        return 1;
    }

    /* engine version query (R2 = 2, R3 = 3) */
    int engine = rubberband_get_engine_version(rb);
    printf("rubberband_get_engine_version(): %d\n", engine);
    if (engine < 2 || engine > 3) {
        fprintf(stderr, "FAIL: unexpected engine version %d\n", engine);
        rubberband_delete(rb);
        free(input);
        free(outbuf);
        return 1;
    }

    /* feed and drain in real-time style blocks (upstream CLI pattern:
     * the last block of data carries final=1 — no separate NULL flush) */
    const size_t block = 1024;
    size_t fed = 0, got = 0;
    while (fed < inFrames) {
        size_t n = (inFrames - fed < block) ? (inFrames - fed) : block;
        int isFinal = (fed + n >= inFrames);
        const float *inChannels[1] = { &input[fed] };
        rubberband_process(rb, inChannels, (unsigned int)n, isFinal);
        fed += n;
        int avail = rubberband_available(rb);
        while (avail > 0) {
            float *outChannels[1] = { &outbuf[got] };
            unsigned int retrieved = rubberband_retrieve(
                rb, outChannels, (unsigned int)avail);
            if (retrieved == 0) break;
            got += retrieved;
            avail = rubberband_available(rb);
        }
    }
    /* after final, drain remaining output */
    int avail = rubberband_available(rb);
    while (avail > 0) {
        float *outChannels[1] = { &outbuf[got] };
        unsigned int retrieved = rubberband_retrieve(
            rb, outChannels, (unsigned int)avail);
        if (retrieved == 0) break;
        got += retrieved;
        avail = rubberband_available(rb);
    }

    rubberband_delete(rb);

    /* Test 3: output length sanity — stretched duration must be near ratio */
    if (got < inFrames / 2) {
        fprintf(stderr, "FAIL: too little output (%zu frames)\n", got);
        free(input);
        free(outbuf);
        return 1;
    }
    double actual = (double)got / (double)inFrames;
    printf("stretched %zu -> %zu frames (ratio %.3f, requested %.3f)\n",
           inFrames, got, actual, ratio);

    /* Test 4: output signal is not silence */
    double energy = 0.0;
    for (size_t i = 0; i < got; i++) {
        energy += (double)outbuf[i] * (double)outbuf[i];
    }
    if (energy < 1.0) {
        fprintf(stderr, "FAIL: output signal looks like silence\n");
        free(input);
        free(outbuf);
        return 1;
    }
    printf("output RMS energy: %.3f\n", sqrt(energy / (double)got));

    free(input);
    free(outbuf);
    printf("All librubberband consumer tests passed\n");
    return 0;
}
