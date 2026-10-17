#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "zmatlib.h"

/* Exercise the real zmat API: compress with every codec, decompress back,
 * verify round-trip byte-identity. Returns non-zero on any failure. */
static const char *meth_name(int id) {
    switch (id) {
        case zmZlib: return "zlib";
        case zmGzip: return "gzip";
        case zmBase64: return "base64";
        case zmLzip: return "lzip";
        case zmLzma: return "lzma";
        case zmLz4: return "lz4";
        case zmLz4hc: return "lz4hc";
        case zmZstd: return "zstd";
        case zmBlosc2Blosclz: return "blosc2blosclz";
        case zmBlosc2Lz4: return "blosc2lz4";
        case zmBlosc2Lz4hc: return "blosc2lz4hc";
        case zmBlosc2Zlib: return "blosc2zlib";
        case zmBlosc2Zstd: return "blosc2zstd";
        default: return "unknown";
    }
}

int main(void) {
    size_t N = 65536;
    unsigned char *buf = (unsigned char*)malloc(N);
    if (!buf) { printf("malloc failed\n"); return 1; }
    for (size_t i = 0; i < N; i++) buf[i] = (unsigned char)((i * 7 + i / 3) % 251);

    int methods[] = {zmZlib, zmGzip, zmLzip, zmLzma, zmLz4, zmLz4hc, zmZstd,
                     zmBlosc2Blosclz, zmBlosc2Lz4, zmBlosc2Lz4hc, zmBlosc2Zlib, zmBlosc2Zstd};
    int nfailed = 0;
    for (unsigned m = 0; m < sizeof(methods)/sizeof(methods[0]); m++) {
        int id = methods[m];
        unsigned char *out = NULL; size_t outlen = 0; int ret = -1;
        unsigned char *dec = NULL; size_t declen = 0;
        int rc = zmat_run(N, buf, &outlen, &out, id, &ret, 1);
        if (rc != 0) {
            printf("FAIL: compress(%s) rc=%d ret=%d\n", meth_name(id), rc, ret);
            nfailed++; continue;
        }
        rc = zmat_run(outlen, out, &declen, &dec, id, &ret, 0);
        int match = (rc == 0 && declen == N && memcmp(dec, buf, N) == 0);
        printf("method=%-12s compress ok (%zu bytes) decompress match=%d\n",
               meth_name(id), outlen, match);
        if (!match) nfailed++;
        free(out); free(dec);
    }
    /* also exercise encode/decode helpers (base64) */
    {
        unsigned char *enc = NULL; size_t enclen = 0; int ret = -1;
        unsigned char *dec = NULL; size_t declen = 0;
        size_t slen = 37; unsigned char *s = buf;
        if (zmat_encode(slen, s, &enclen, &enc, zmBase64, &ret) == 0) {
            int rc = zmat_decode(enclen, enc, &declen, &dec, zmBase64, &ret);
            int match = (rc == 0 && declen == slen && memcmp(dec, s, slen) == 0);
            printf("encode/decode(base64) match=%d\n", match);
            if (!match) nfailed++;
        } else { printf("FAIL: encode(base64)\n"); nfailed++; }
        free(enc); free(dec);
    }
    free(buf);
    printf("zmat test: %d/%u checks failed\n", nfailed, sizeof(methods)/sizeof(methods[0]) + 1);
    return nfailed ? 1 : 0;
}