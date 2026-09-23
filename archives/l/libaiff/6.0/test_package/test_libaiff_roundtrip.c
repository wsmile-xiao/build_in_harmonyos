/* Consumer test: AIFF sample write/read round-trip.
 *
 * Exercises the core libaiff read/write API on the installed package:
 * Open(F_WRONLY) -> SetAudioFormat -> StartWritingSamples ->
 * WriteSamples32Bit -> EndWritingSamples -> Close -> Open(F_RDONLY) ->
 * GetAudioFormat -> ReadSamples32Bit -> Seek -> re-read.
 * Each stage prints one CHECK-OK line; the conanfile counts them for the
 * HMBS_TEST_PACKAGE_RESULT marker (exit 0 alone is not proof).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libaiff/libaiff.h>
#include <stdint.h>

#define FRAMES 8

int main(void)
{
    AIFF_Ref w;
    AIFF_Ref r;
    /* 16-bit AIFF stores only the high 16 bits (upstream libaiff.c:
     * write: words[i] = samples[i] >> 16, read: samples[i] = p[i] << 16),
     * so round-trip values must have zero low 16 bits to be bit-exact.
     * Each entry below is (int16 value) << 16. */
    int32_t out[FRAMES] = {0, 65536, -65536, 2147418112, INT32_MIN,
                           8060928, -8060928, 2752512};
    int32_t in[FRAMES];
    int32_t again[FRAMES];
    uint64_t nSamples = 0;
    int channels = 0;
    double rate = 0.0;
    int bits = 0;
    int seg = 0;
    int got;
    int i;
    const char *path;
    char tmp[256];

    path = getenv("LIBAIFF_TEST_TMP");
    if (path == NULL || path[0] == '\0') {
        path = "libaiff_roundtrip.aiff";
    }
    snprintf(tmp, sizeof(tmp), "%s_rt.aiff", path);

    w = AIFF_OpenFile(tmp, F_WRONLY);
    if (w == NULL) {
        printf("FAIL open-write\n");
        return 1;
    }
    printf("CHECK-OK: open-write\n");

    if (!AIFF_SetAudioFormat(w, 1, 44100.0, 16)) {
        printf("FAIL set-audio-format\n");
        AIFF_CloseFile(w);
        return 1;
    }
    printf("CHECK-OK: set-audio-format\n");

    if (!AIFF_StartWritingSamples(w)) {
        printf("FAIL start-writing\n");
        AIFF_CloseFile(w);
        return 1;
    }
    /* Upstream lpcm_write_lpcm returns 1 on success (not a sample count);
     * AIFF_WriteSamples32Bit forwards that status for segmentSize != 4. */
    if (AIFF_WriteSamples32Bit(w, out, FRAMES) != 1) {
        printf("FAIL write-samples\n");
        AIFF_CloseFile(w);
        return 1;
    }
    printf("CHECK-OK: write-samples\n");

    if (!AIFF_EndWritingSamples(w)) {
        printf("FAIL end-writing\n");
        AIFF_CloseFile(w);
        return 1;
    }
    /* AIFF_CloseFile returns 1 on successful write-close (see
     * AIFF_WriteClose: ret=1 when stat==3, -1 on I/O error). */
    {
        int closeRc = AIFF_CloseFile(w);
        if (closeRc != 1) {
            printf("FAIL close-write rc=%d\n", closeRc);
            return 1;
        }
    }
    printf("CHECK-OK: close-write\n");

    r = AIFF_OpenFile(tmp, F_RDONLY);
    if (r == NULL) {
        printf("FAIL open-read\n");
        return 1;
    }
    if (!AIFF_GetAudioFormat(r, &nSamples, &channels, &rate, &bits, &seg)) {
        printf("FAIL get-audio-format\n");
        AIFF_CloseFile(r);
        return 1;
    }
    if (channels != 1 || bits != 16 || (int)rate != 44100) {
        printf("FAIL audio-format-mismatch ch=%d bits=%d rate=%f\n",
               channels, bits, rate);
        AIFF_CloseFile(r);
        return 1;
    }
    printf("CHECK-OK: audio-format\n");

    memset(in, 0, sizeof(in));
    got = AIFF_ReadSamples32Bit(r, in, FRAMES);
    if (got != FRAMES) {
        printf("FAIL read-samples got=%d\n", got);
        AIFF_CloseFile(r);
        return 1;
    }
    for (i = 0; i < FRAMES; i++) {
        if (in[i] != out[i]) {
            printf("FAIL sample-mismatch [%d] %d != %d\n", i, in[i], out[i]);
            AIFF_CloseFile(r);
            return 1;
        }
    }
    printf("CHECK-OK: read-samples\n");

    if (!AIFF_Seek(r, 0)) {
        printf("FAIL seek\n");
        AIFF_CloseFile(r);
        return 1;
    }
    memset(again, 0, sizeof(again));
    got = AIFF_ReadSamples32Bit(r, again, FRAMES);
    if (got != FRAMES || memcmp(again, out, sizeof(out)) != 0) {
        printf("FAIL re-read got=%d\n", got);
        AIFF_CloseFile(r);
        return 1;
    }
    AIFF_CloseFile(r);
    remove(tmp);
    printf("CHECK-OK: seek-reread\n");
    return 0;
}
