/* test_wavpack.c — Conan L1 test for wavpack 5.9.0
 * Verifies: library version, encode (pack) -> decode (unpack) roundtrip.
 * Creates a WavPack file with 100 mono 16-bit samples at 44100 Hz,
 * reads it back, and confirms the decoded samples match the originals. */
#include <wavpack/wavpack.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NUM_SAMPLES 100
#define SAMPLE_RATE 44100
#define TEST_FILE "test_roundtrip.wv"

/* Block output callback: writes encoded data to a FILE*. */
static int block_output(void *id, void *data, int32_t bcount) {
    FILE *file = (FILE *)id;
    return fwrite(data, 1, bcount, file) == (size_t)bcount ? 1 : 0;
}

int main(void) {
    int rc = 1;            /* default to failure */
    FILE *out = NULL;
    WavpackContext *wpc_out = NULL;
    WavpackContext *wpc_in = NULL;

    /* 1. Verify library version string */
    const char *ver = WavpackGetLibraryVersionString();
    if (ver == NULL || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: WavpackGetLibraryVersionString returned empty\n");
        goto cleanup;
    }
    printf("OK: WavPack library version = %s\n", ver);

    /* 2. Generate test samples (simple ramp)
     * Use multiplier 300 so max value = 99 * 300 = 29700, safely within
     * int16_t range [-32768, 32767]. With bits_per_sample=16, larger values
     * (e.g. i*1000 -> 33000 at i=33) overflow and decode as negative numbers. */
    int32_t samples[NUM_SAMPLES];
    for (int i = 0; i < NUM_SAMPLES; i++) {
        samples[i] = (int32_t)(i * 300);
    }

    /* 3. Encode: create WavPack file */
    out = fopen(TEST_FILE, "wb");
    if (!out) {
        fprintf(stderr, "FAIL: cannot open %s for writing\n", TEST_FILE);
        goto cleanup;
    }

    wpc_out = WavpackOpenFileOutput(block_output, out, NULL);
    if (!wpc_out) {
        fprintf(stderr, "FAIL: WavpackOpenFileOutput returned NULL\n");
        goto cleanup;
    }

    WavpackConfig config;
    memset(&config, 0, sizeof(config));
    config.num_channels = 1;
    config.sample_rate = SAMPLE_RATE;
    config.bits_per_sample = 16;
    config.bytes_per_sample = 2;

    if (!WavpackSetConfiguration(wpc_out, &config, NUM_SAMPLES)) {
        fprintf(stderr, "FAIL: WavpackSetConfiguration failed\n");
        goto cleanup;
    }

    if (!WavpackPackInit(wpc_out)) {
        fprintf(stderr, "FAIL: WavpackPackInit failed\n");
        goto cleanup;
    }

    if (!WavpackPackSamples(wpc_out, samples, NUM_SAMPLES)) {
        fprintf(stderr, "FAIL: WavpackPackSamples failed\n");
        goto cleanup;
    }

    if (!WavpackFlushSamples(wpc_out)) {
        fprintf(stderr, "FAIL: WavpackFlushSamples failed\n");
        goto cleanup;
    }
    WavpackCloseFile(wpc_out);
    wpc_out = NULL;
    fclose(out);
    out = NULL;
    printf("OK: encoded %d samples to %s\n", NUM_SAMPLES, TEST_FILE);

    /* 4. Decode: read back and verify */
    char error[80] = {0};
    wpc_in = WavpackOpenFileInput(TEST_FILE, error, 0, 0);
    if (!wpc_in) {
        fprintf(stderr, "FAIL: WavpackOpenFileInput failed: %s\n", error);
        goto cleanup;
    }

    int32_t num_samples = WavpackGetNumSamples(wpc_in);
    if (num_samples < 0) {
        fprintf(stderr, "FAIL: WavpackGetNumSamples returned error\n");
        goto cleanup;
    }
    if (num_samples != NUM_SAMPLES) {
        fprintf(stderr, "FAIL: expected %d samples, got %d\n", NUM_SAMPLES, num_samples);
        goto cleanup;
    }

    int32_t rate = WavpackGetSampleRate(wpc_in);
    if (rate != SAMPLE_RATE) {
        fprintf(stderr, "FAIL: expected sample rate %d, got %d\n", SAMPLE_RATE, rate);
        goto cleanup;
    }

    int32_t read_buf[NUM_SAMPLES];
    int32_t unpacked = WavpackUnpackSamples(wpc_in, read_buf, NUM_SAMPLES);
    if (unpacked < 0) {
        fprintf(stderr, "FAIL: WavpackUnpackSamples returned error\n");
        goto cleanup;
    }
    if (unpacked != NUM_SAMPLES) {
        fprintf(stderr, "FAIL: expected to unpack %d samples, got %d\n", NUM_SAMPLES, unpacked);
        goto cleanup;
    }

    /* 5. Verify decoded samples match originals */
    for (int i = 0; i < NUM_SAMPLES; i++) {
        if (read_buf[i] != samples[i]) {
            fprintf(stderr, "FAIL: sample %d mismatch: original=%d, decoded=%d\n",
                    i, samples[i], read_buf[i]);
            goto cleanup;
        }
    }

    WavpackCloseFile(wpc_in);
    wpc_in = NULL;
    printf("OK: roundtrip verified — %d samples, rate=%d\n", num_samples, rate);
    printf("All tests passed\n");
    rc = 0;                /* success */

cleanup:
    if (wpc_in) WavpackCloseFile(wpc_in);
    if (wpc_out) WavpackCloseFile(wpc_out);
    if (out) fclose(out);
    /* Clean up temporary test file on all paths (success and failure). */
    if (remove(TEST_FILE) != 0 && rc == 0)
        perror("remove " TEST_FILE);
    return rc;
}
