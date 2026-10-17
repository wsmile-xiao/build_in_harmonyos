/* test_decode.c — distorm 消费者测试：decompose 与多字节指令解码 */
#include <stdio.h>
#include <string.h>

#include "distorm.h"

#define MAX_INSTRUCTIONS (32)

int main(void) {
    /* 1. Decompose the 3-byte sequence used by the upstream demo program. */
    unsigned char raw[] = { 0x0f, 0x01, 0xcb };
    _DInst decomposed[MAX_INSTRUCTIONS];
    unsigned int decomposedCount = 0;
    _CodeInfo ci;

    ci.codeOffset = 0;
    ci.code = raw;
    ci.codeLen = sizeof(raw);
    ci.dt = Decode32Bits;
    ci.features = DF_NONE;
    ci.addrMask = 0;
    ci.nextOffset = 0;

    if (distorm_decompose(&ci, decomposed, MAX_INSTRUCTIONS, &decomposedCount) == DECRES_INPUTERR) {
        fprintf(stderr, "distorm_decompose input error\n");
        return 1;
    }
    if (decomposedCount != 1) {
        fprintf(stderr, "unexpected decomposed count: %u\n", decomposedCount);
        return 1;
    }
    if (decomposed[0].flags == FLAG_NOT_DECODABLE) {
        fprintf(stderr, "upstream demo bytes did not decode\n");
        return 1;
    }
    if (decomposed[0].size != 3) {
        fprintf(stderr, "unexpected decomposed size: %u\n", decomposed[0].size);
        return 1;
    }
    printf("decompose demo bytes: OK (count=1 size=3)\n");

    /* 2. Decode MOV EAX, 0x12345678 (B8 78 56 34 12) in 32-bit mode. */
    unsigned char mov32[] = { 0xb8, 0x78, 0x56, 0x34, 0x12 };
    _DecodedInst result[MAX_INSTRUCTIONS];
    unsigned int used = 0;
    _DecodeResult res = distorm_decode(0, mov32, sizeof(mov32), Decode32Bits,
                                       result, MAX_INSTRUCTIONS, &used);
    if (res != DECRES_SUCCESS) {
        fprintf(stderr, "distorm_decode (mov32) failed: %d\n", (int)res);
        return 1;
    }
    if (used != 1) {
        fprintf(stderr, "unexpected mov32 count: %u\n", used);
        return 1;
    }
    if (result[0].size != 5) {
        fprintf(stderr, "unexpected mov32 size: %u\n", result[0].size);
        return 1;
    }
    if (strcmp((const char *)result[0].mnemonic.p, "MOV") != 0) {
        fprintf(stderr, "unexpected mov32 mnemonic: %s\n", result[0].mnemonic.p);
        return 1;
    }
    if (strstr((const char *)result[0].operands.p, "12345678") == NULL) {
        fprintf(stderr, "unexpected mov32 operands: %s\n", result[0].operands.p);
        return 1;
    }
    printf("decode MOV EAX, 0x12345678: OK (size=5 operands=%s)\n", result[0].operands.p);

    /* 3. Decode MOV RAX, 0xdeadbeef (48 B8 ...) in 64-bit mode. */
    unsigned char mov64[] = { 0x48, 0xb8, 0xef, 0xbe, 0xad, 0xde, 0x00, 0x00, 0x00, 0x00 };
    used = 0;
    res = distorm_decode(0, mov64, sizeof(mov64), Decode64Bits,
                         result, MAX_INSTRUCTIONS, &used);
    if (res != DECRES_SUCCESS) {
        fprintf(stderr, "distorm_decode (mov64) failed: %d\n", (int)res);
        return 1;
    }
    if (used != 1 || result[0].size != 10) {
        fprintf(stderr, "unexpected mov64 count/size: %u/%u\n", used, result[0].size);
        return 1;
    }
    if (strcmp((const char *)result[0].mnemonic.p, "MOV") != 0) {
        fprintf(stderr, "unexpected mov64 mnemonic: %s\n", result[0].mnemonic.p);
        return 1;
    }
    printf("decode MOV RAX, imm64: OK (size=10 operands=%s)\n", result[0].operands.p);

    /* 4. Two NOPs must decode to exactly two instructions. */
    unsigned char nops[] = { 0x90, 0x90 };
    used = 0;
    res = distorm_decode(0, nops, sizeof(nops), Decode32Bits,
                         result, MAX_INSTRUCTIONS, &used);
    if (res != DECRES_SUCCESS || used != 2) {
        fprintf(stderr, "unexpected nops result: %d/%u\n", (int)res, used);
        return 1;
    }
    printf("decode NOP NOP: OK (count=2)\n");
    return 0;
}
