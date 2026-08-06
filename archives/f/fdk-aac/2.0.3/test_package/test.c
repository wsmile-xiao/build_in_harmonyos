#include <fdk-aac/aacenc_lib.h>
#include <fdk-aac/aacdecoder_lib.h>
#include <stdio.h>

int main(void) {
    /* Test 1: Open encoder, verify success, then close */
    HANDLE_AACENCODER hAacEncoder = NULL;
    AACENC_ERROR err = aacEncOpen(&hAacEncoder, 0, 0);
    if (err != AACENC_OK) {
        fprintf(stderr, "aacEncOpen failed: 0x%x\n", err);
        return 1;
    }
    aacEncClose(&hAacEncoder);

    /* Test 2: Open decoder, verify success, then close */
    HANDLE_AACDECODER hAacDecoder = aacDecoder_Open(TT_MP4_RAW, 0);
    if (hAacDecoder == NULL) {
        fprintf(stderr, "aacDecoder_Open failed\n");
        return 1;
    }
    aacDecoder_Close(hAacDecoder);

    printf("fdk-aac encoder/decoder open/close test: OK\n");
    return 0;
}
