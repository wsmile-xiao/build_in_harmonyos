#include <stdio.h>
#include <string.h>

#include <qcbor/qcbor.h>
#include <qcbor/qcbor_spiffy_decode.h>

static const char kMsg[] = "hello qcbor";

int main(void) {
    /* Encode {"greeting": "hello qcbor", "answer": 42} as a CBOR map. */
    UsefulBuf_MAKE_STACK_UB(storage, 256);
    QCBOREncodeContext enc;
    QCBOREncode_Init(&enc, storage);
    QCBOREncode_OpenMap(&enc);
    QCBOREncode_AddSZStringToMap(&enc, "greeting", kMsg);
    QCBOREncode_AddInt64ToMap(&enc, "answer", 42);
    QCBOREncode_CloseMap(&enc);

    UsefulBufC cbor;
    if (QCBOREncode_Finish(&enc, &cbor) != QCBOR_SUCCESS) {
        fprintf(stderr, "consumer: encode failed\n");
        return 1;
    }

    /* Decode it back and assert both entries round-trip. */
    QCBORDecodeContext dec;
    QCBORDecode_Init(&dec, cbor, QCBOR_DECODE_MODE_MAP_STRINGS_ONLY);
    QCBORDecode_EnterMap(&dec, NULL);

    UsefulBufC greeting;
    QCBORDecode_GetTextStringInMapSZ(&dec, "greeting", &greeting);
    if (QCBORDecode_GetError(&dec) != QCBOR_SUCCESS ||
        greeting.len != strlen(kMsg) ||
        memcmp(greeting.ptr, kMsg, greeting.len) != 0) {
        fprintf(stderr, "consumer: string round-trip mismatch\n");
        return 1;
    }

    int64_t answer = 0;
    QCBORDecode_GetInt64InMapSZ(&dec, "answer", &answer);
    if (QCBORDecode_GetError(&dec) != QCBOR_SUCCESS || answer != 42) {
        fprintf(stderr, "consumer: int round-trip mismatch\n");
        return 1;
    }

    QCBORDecode_ExitMap(&dec);
    if (QCBORDecode_Finish(&dec) != QCBOR_SUCCESS) {
        fprintf(stderr, "consumer: decode finish failed\n");
        return 1;
    }

    printf("qcbor consumer OK: %zu-byte CBOR map round-tripped\n", (size_t)cbor.len);
    return 0;
}
