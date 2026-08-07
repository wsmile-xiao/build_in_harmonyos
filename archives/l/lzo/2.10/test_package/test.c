/* test_package/test.c — LZO compression/decompression test (R34: substantive test) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lzo/lzo1x.h>
#include <lzo/lzoconf.h>

#define IN_LEN  (128 * 1024)
#define OUT_LEN (IN_LEN + IN_LEN / 16 + 64 + 3)

int main(void) {
    lzo_uint in_len, out_len, new_len;
    unsigned char *in_buf, *out_buf, *new_buf, *wrk;
    int r;

    if (lzo_init() != LZO_E_OK) {
        printf("lzo_init() failed\n");
        return 1;
    }

    in_buf = (unsigned char *)malloc(IN_LEN);
    out_buf = (unsigned char *)malloc(OUT_LEN);
    new_buf = (unsigned char *)malloc(IN_LEN);
    wrk = (unsigned char *)malloc(LZO1X_1_MEM_COMPRESS);

    if (!in_buf || !out_buf || !new_buf || !wrk) {
        printf("memory allocation failed\n");
        free(in_buf); free(out_buf); free(new_buf); free(wrk);
        return 1;
    }

    in_len = IN_LEN;
    memset(in_buf, 0xAA, in_len);

    out_len = OUT_LEN;
    r = lzo1x_1_compress(in_buf, in_len, out_buf, &out_len, wrk);
    if (r != LZO_E_OK) {
        printf("lzo1x_1_compress failed: %d\n", r);
        free(in_buf); free(out_buf); free(new_buf); free(wrk);
        return 1;
    }

    new_len = IN_LEN;
    r = lzo1x_decompress(out_buf, out_len, new_buf, &new_len, NULL);
    if (r != LZO_E_OK) {
        printf("lzo1x_decompress failed: %d\n", r);
        free(in_buf); free(out_buf); free(new_buf); free(wrk);
        return 1;
    }

    if (new_len != in_len) {
        printf("length mismatch: %lu != %lu\n",
               (unsigned long)new_len, (unsigned long)in_len);
        free(in_buf); free(out_buf); free(new_buf); free(wrk);
        return 1;
    }

    if (memcmp(in_buf, new_buf, in_len) != 0) {
        printf("data mismatch after round-trip\n");
        free(in_buf); free(out_buf); free(new_buf); free(wrk);
        return 1;
    }

    printf("lzo compression/decompression test: OK (compressed %lu -> %lu)\n",
           (unsigned long)in_len, (unsigned long)out_len);

    free(in_buf);
    free(out_buf);
    free(new_buf);
    free(wrk);
    return 0;
}
