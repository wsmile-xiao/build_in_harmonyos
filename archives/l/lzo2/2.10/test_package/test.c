#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lzo/lzo1x.h>
#include <lzo/lzoconf.h>

int main(void) {
    if (lzo_init() != LZO_E_OK) {
        printf("lzo_init() failed\n");
        return 1;
    }

    const char *ver = lzo_version_string();
    printf("LZO version: %s\n", ver);

    const char *in = "Hello, LZO compression on HarmonyOS! Hello, LZO compression on HarmonyOS!";
    lzo_uint in_len = strlen(in);
    lzo_uint out_len = in_len + in_len / 16 + 64 + 3;
    unsigned char buf_out[256];
    unsigned char buf_decompressed[256];
    lzo_uint decompressed_len = sizeof(buf_decompressed);
    lzo_voidp wrkmem = (lzo_voidp)malloc(LZO1X_1_MEM_COMPRESS);

    if (wrkmem == NULL) {
        printf("malloc failed\n");
        return 1;
    }

    int r = lzo1x_1_compress((const lzo_bytep)in, in_len, buf_out, &out_len, wrkmem);
    if (r != LZO_E_OK) {
        printf("lzo1x_1_compress failed: %d\n", r);
        free(wrkmem);
        return 1;
    }
    printf("Compressed %lu bytes into %lu bytes\n", (unsigned long)in_len, (unsigned long)out_len);

    r = lzo1x_decompress(buf_out, out_len, buf_decompressed, &decompressed_len, NULL);
    if (r != LZO_E_OK) {
        printf("lzo1x_decompress failed: %d\n", r);
        free(wrkmem);
        return 1;
    }
    printf("Decompressed %lu bytes\n", (unsigned long)decompressed_len);

    if (decompressed_len != in_len || memcmp(in, buf_decompressed, in_len) != 0) {
        printf("Round-trip verification FAILED\n");
        free(wrkmem);
        return 1;
    }

    printf("Round-trip verification OK\n");
    free(wrkmem);
    return 0;
}
