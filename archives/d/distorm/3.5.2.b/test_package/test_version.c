/* test_version.c — distorm 消费者测试：版本号与单字节指令解码 */
#include <stdio.h>
#include <string.h>

#include "distorm.h"

#define MAX_INSTRUCTIONS (32)

int main(void) {
    unsigned int dver = distorm_version();
    unsigned int major = (dver >> 16) & 0xff;
    unsigned int minor = (dver >> 8) & 0xff;
    unsigned int build = dver & 0xff;

    if (major != 3) {
        fprintf(stderr, "unexpected major version: %u\n", major);
        return 1;
    }
    if (minor != 5) {
        fprintf(stderr, "unexpected minor version: %u\n", minor);
        return 1;
    }
    if (build != 2) {
        fprintf(stderr, "unexpected build version: %u\n", build);
        return 1;
    }
    printf("distorm version: %u.%u.%u\n", major, minor, build);

    /* Decode a single NOP (0x90) in 32-bit mode. */
    unsigned char code[] = { 0x90 };
    _DecodedInst result[MAX_INSTRUCTIONS];
    unsigned int used = 0;
    _DecodeResult res = distorm_decode(0, code, sizeof(code), Decode32Bits,
                                       result, MAX_INSTRUCTIONS, &used);
    if (res != DECRES_SUCCESS) {
        fprintf(stderr, "distorm_decode failed: %d\n", (int)res);
        return 1;
    }
    if (used != 1) {
        fprintf(stderr, "unexpected instruction count: %u\n", used);
        return 1;
    }
    if (result[0].size != 1) {
        fprintf(stderr, "unexpected NOP size: %u\n", result[0].size);
        return 1;
    }
    if (strcmp((const char *)result[0].mnemonic.p, "NOP") != 0) {
        fprintf(stderr, "unexpected mnemonic: %s\n", result[0].mnemonic.p);
        return 1;
    }
    printf("decode NOP: OK (size=1 mnemonic=NOP)\n");
    return 0;
}
