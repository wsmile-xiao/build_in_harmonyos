#include <mhash.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    static const unsigned char expected[16] = {
        0x90, 0x01, 0x50, 0x98, 0x3c, 0xd2, 0x4f, 0xb0,
        0xd6, 0x96, 0x3f, 0x7d, 0x28, 0xe1, 0x7f, 0x72,
    };
    unsigned char digest[16];
    const char *input = "abc";
    MHASH handle = mhash_init(MHASH_MD5);

    if (handle == MHASH_FAILED) {
        puts("mhash_init failed");
        return 1;
    }
    mhash(handle, input, strlen(input));
    mhash_deinit(handle, digest);
    if (memcmp(digest, expected, sizeof(expected)) != 0) {
        puts("unexpected MD5 digest");
        return 1;
    }
    puts("mhash md5 ok");
    return 0;
}
