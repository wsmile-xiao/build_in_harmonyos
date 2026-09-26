#include <stdio.h>
#include <string.h>

/* 实质调用 libindi 核心 C API：base64 编解码
 * (libindicore 提供, 并入 libindiclient/libindidriver 静态库) */
#include <libindi/base64.h>

int main(void)
{
    const unsigned char input[] = "Hello INDI 2.2.2.1";
    unsigned char encoded[128] = {0};
    char decoded[128] = {0};

    int elen = to64frombits(encoded, input, (int)sizeof(input) - 1);
    if (elen <= 0)
    {
        fprintf(stderr, "FAIL: to64frombits returned %d\n", elen);
        return 1;
    }

    int dlen = from64tobits(decoded, (const char *)encoded);
    if (dlen <= 0)
    {
        fprintf(stderr, "FAIL: from64tobits returned %d\n", dlen);
        return 1;
    }

    if (dlen != (int)sizeof(input) - 1 || memcmp(decoded, input, (size_t)dlen) != 0)
    {
        fprintf(stderr, "FAIL: base64 roundtrip mismatch (dlen=%d)\n", dlen);
        return 1;
    }

    printf("libindi base64 roundtrip OK: '%s' (%d bytes)\n", decoded, dlen);
    return 0;
}
