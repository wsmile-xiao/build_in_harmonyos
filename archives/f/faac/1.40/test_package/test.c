/*
 * test_package/test.c — faac L1 test
 * Exercises the faac encoding API: open encoder, configure, encode PCM, close.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "faac.h"
#include "faaccfg.h"

int main(void) {
    /* 1. Get version info */
    char *faac_id = NULL;
    char *faac_copyright = NULL;
    int cfg_ver = faacEncGetVersion(&faac_id, &faac_copyright);
    if (cfg_ver != FAAC_CFG_VERSION) {
        fprintf(stderr, "FAIL: version mismatch (got %d, expected %d)\n",
                cfg_ver, FAAC_CFG_VERSION);
        return 1;
    }
    printf("faac version: %s (cfg %d)\n", faac_id ? faac_id : "?", cfg_ver);

    /* 2. Open encoder — 44100 Hz, mono */
    unsigned long sampleRate = 44100;
    unsigned int numChannels = 1;
    unsigned long inputSamples = 0;
    unsigned long maxOutputBytes = 0;

    faacEncHandle hEncoder = faacEncOpen(sampleRate, numChannels,
                                         &inputSamples, &maxOutputBytes);
    if (!hEncoder) {
        fprintf(stderr, "FAIL: faacEncOpen returned NULL\n");
        return 1;
    }
    printf("faacEncOpen OK: inputSamples=%lu, maxOutputBytes=%lu\n",
           inputSamples, maxOutputBytes);

    /* 3. Get and configure */
    faacEncConfigurationPtr cfg = faacEncGetCurrentConfiguration(hEncoder);
    if (!cfg) {
        fprintf(stderr, "FAIL: faacEncGetCurrentConfiguration returned NULL\n");
        faacEncClose(hEncoder);
        return 1;
    }
    cfg->outputFormat = ADTS_STREAM;
    cfg->inputFormat = FAAC_INPUT_16BIT;
    cfg->aacObjectType = LOW;
    cfg->mpegVersion = MPEG4;

    if (!faacEncSetConfiguration(hEncoder, cfg)) {
        fprintf(stderr, "FAIL: faacEncSetConfiguration returned 0\n");
        faacEncClose(hEncoder);
        return 1;
    }
    printf("faacEncSetConfiguration OK (ADTS, MPEG4, LC)\n");

    /* 4. Encode one frame of PCM (silence) */
    int32_t *pcm = (int32_t *)calloc(inputSamples, sizeof(int32_t));
    if (!pcm) {
        fprintf(stderr, "FAIL: calloc failed\n");
        faacEncClose(hEncoder);
        return 1;
    }
    unsigned char *outbuf = (unsigned char *)malloc(maxOutputBytes);
    if (!outbuf) {
        fprintf(stderr, "FAIL: malloc failed\n");
        free(pcm);
        faacEncClose(hEncoder);
        return 1;
    }

    int bytesWritten = faacEncEncode(hEncoder, (int32_t *)pcm, inputSamples,
                                     outbuf, maxOutputBytes);
    if (bytesWritten < 0) {
        fprintf(stderr, "FAIL: faacEncEncode returned %d\n", bytesWritten);
        free(pcm);
        free(outbuf);
        faacEncClose(hEncoder);
        return 1;
    }
    printf("faacEncEncode OK: %d bytes encoded\n", bytesWritten);

    /* 5. Close encoder */
    faacEncClose(hEncoder);
    printf("faacEncClose OK\n");

    free(pcm);
    free(outbuf);

    printf("ALL TESTS PASSED\n");
    return 0;
}
