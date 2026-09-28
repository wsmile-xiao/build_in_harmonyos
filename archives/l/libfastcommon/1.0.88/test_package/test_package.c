#include <stdio.h>
#include <string.h>
#include "fastcommon/md5.h"
#include "fastcommon/logger.h"

int main(void)
{
    MD5_CTX ctx;
    unsigned char digest[16];
    char hex[33];
    int i;

    if (log_init() != 0) {
        fprintf(stderr, "log_init failed\n");
        return 1;
    }

    my_md5_init(&ctx);
    my_md5_update(&ctx, (unsigned char *)"libfastcommon", 13);
    my_md5_final(digest, &ctx);
    for (i = 0; i < 16; i++) {
        sprintf(hex + i * 2, "%02x", digest[i]);
    }
    hex[32] = '\0';
    /* md5("libfastcommon") = a784d967ffe962ef8fd6dfbdcc0b908f */
    if (strcmp(hex, "a784d967ffe962ef8fd6dfbdcc0b908f") != 0) {
        fprintf(stderr, "md5 mismatch: %s\n", hex);
        return 2;
    }
    printf("test_package OK, md5=%s\n", hex);
    return 0;
}