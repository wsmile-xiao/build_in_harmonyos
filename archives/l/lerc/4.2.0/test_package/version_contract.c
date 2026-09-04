#include <stdio.h>
#include <Lerc_c_api.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

int main(void) {
    /* Version macros from Lerc_c_api.h */
    CHECK(LERC_VERSION_MAJOR == 4, "LERC_VERSION_MAJOR == 4");
    CHECK(LERC_VERSION_MINOR == 2, "LERC_VERSION_MINOR == 2");
    CHECK(LERC_VERSION_PATCH == 0, "LERC_VERSION_PATCH == 0");
    CHECK(LERC_VERSION_NUMBER == 40200, "LERC_VERSION_NUMBER == 40200");

    /* LERC_AT_LEAST_VERSION is a boolean (>=) comparison, not an exact match */
    CHECK(LERC_AT_LEAST_VERSION(4, 0, 0), "LERC_AT_LEAST_VERSION(4,0,0)");
    CHECK(LERC_AT_LEAST_VERSION(4, 2, 0), "LERC_AT_LEAST_VERSION(4,2,0)");
    CHECK(!LERC_AT_LEAST_VERSION(4, 3, 0), "!LERC_AT_LEAST_VERSION(4,3,0)");

    /* lerc_status is an alias for unsigned int */
    CHECK(sizeof(lerc_status) == sizeof(unsigned int),
          "sizeof(lerc_status) == sizeof(unsigned int)");

    /* Compile-time signature contract: assigning &lerc_encode to a typed
     * function pointer fails to compile if the upstream signature ever
     * changes (checked under -Werror). lerc_encode(pData, dataType, nDepth,
     * nCols, nRows, nBands, nMasks, pValidBytes, maxZErr, pOutBuffer,
     * outBufferSize, nBytesWritten) */
    static lerc_status (*const sig_lerc_encode)(
        const void *, unsigned int, int, int, int, int, int,
        const unsigned char *, double, unsigned char *, unsigned int,
        unsigned int *) = lerc_encode;
    (void)sig_lerc_encode;
    printf("ok: lerc_encode signature contract\n");

    /* Compile-time signature contract: lerc_decode_4D(pLercBlob, blobSize,
     * nMasks, pValidBytes, nDepth, nCols, nRows, nBands, dataType, pData,
     * pUsesNoData, noDataValues) */
    static lerc_status (*const sig_lerc_decode_4D)(
        const unsigned char *, unsigned int, int, unsigned char *, int,
        int, int, int, unsigned int, void *, unsigned char *,
        double *) = lerc_decode_4D;
    (void)sig_lerc_decode_4D;
    printf("ok: lerc_decode_4D signature contract\n");

    /* Real functional round-trip: encode a tiny 2x2 float image, then decode
     * it back. This actually calls lerc_computeCompressedSize / lerc_encode /
     * lerc_decode_4D, all exported by libLerc.so.4, binding the test to the
     * built library (maxZErr = 0 is lossless for float per the upstream docs). */
    {
        const float input[4] = {1.0f, 2.0f, 3.0f, 4.0f};
        float output[4] = {0.0f, 0.0f, 0.0f, 0.0f};
        unsigned char blob[512];
        unsigned int blobSize = 0, nBytesWritten = 0;
        lerc_status st;
        int i;

        st = lerc_computeCompressedSize(input, 6 /* float */, 1 /* nDepth */,
                                        2 /* nCols */, 2 /* nRows */,
                                        1 /* nBands */, 0 /* nMasks */,
                                        NULL /* all valid */, 0.0 /* lossless */,
                                        &blobSize);
        CHECK(st == 0, "lerc_computeCompressedSize returns Ok");
        CHECK(blobSize > 0, "compressed blob size > 0");
        if (blobSize > sizeof(blob)) {
            blobSize = sizeof(blob);
        }

        st = lerc_encode(input, 6, 1, 2, 2, 1, 0, NULL, 0.0,
                         blob, blobSize, &nBytesWritten);
        CHECK(st == 0, "lerc_encode returns Ok");
        CHECK(nBytesWritten > 0, "lerc_encode wrote data");

        st = lerc_decode_4D(blob, nBytesWritten, 0 /* nMasks */, NULL,
                            1, 2, 2, 1, 6, output, NULL, NULL);
        CHECK(st == 0, "lerc_decode_4D returns Ok");
        for (i = 0; i < 4; i++) {
            CHECK(output[i] == input[i], "lerc round-trip preserves pixel");
        }
        printf("ok: lerc encode/decode round-trip\n");
    }

    printf("lerc version contract: all checks passed\n");
    return 0;
}
