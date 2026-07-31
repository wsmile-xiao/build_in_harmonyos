#include <stdio.h>
#include <stdlib.h>
#include "keystone/keystone.h"

int main(void) {
    unsigned int major = 0, minor = 0;
    unsigned int ver = ks_version(&major, &minor);
    if (major != KS_API_MAJOR || minor != KS_API_MINOR) {
        printf("keystone version mismatch: got %u.%u, expected %u.%u\n",
               major, minor, KS_API_MAJOR, KS_API_MINOR);
        return 1;
    }
    printf("keystone version: %u.%u (0x%x)\n", major, minor, ver);

    ks_engine *ks = NULL;
    ks_err err = ks_open(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN, &ks);
    if (err != KS_ERR_OK) {
        printf("FAIL: ks_open returned %u (%s)\n", err, ks_strerror(err));
        return 1;
    }

    unsigned char *encode = NULL;
    size_t size = 0, count = 0;
    const char *assembly = "mov x0, #0x1";
    // ks_asm() returns int: 0 on success, -1 on failure (keystone.h L250).
    // NOTE: count (stat_count, via pointer) is the # of statements, NOT the
    // return value. See official samples/sample.c: if(ks_asm(...)){FAIL}else{OK}.
    if (ks_asm(ks, assembly, 0, &encode, &size, &count) != 0) {
        printf("FAIL: ks_asm(\"%s\") failed: %s\n", assembly, ks_strerror(ks_errno(ks)));
        ks_close(ks);
        return 1;
    }

    printf("Assembled \"%s\" -> %zu bytes, %zu statements:", assembly, size, count);
    for (size_t i = 0; i < size; i++) {
        printf(" %02x", encode[i]);
    }
    printf("\n");

    ks_free(encode);
    ks_close(ks);

    printf("test keystone 0.9.2: OK\n");
    return 0;
}
