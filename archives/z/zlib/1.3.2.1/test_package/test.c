/*
 * test_package/test.c — 消费者视角真实调用 zlib API（R34，禁止空壳 print-only）。
 *
 * 覆盖：zlibVersion()、compress/uncompress 往返、compress2/uncompress2、
 *       compressBound、adler32、crc32、deflate/inflate 基础往返、gzopen/gzwrite/gzread。
 *
 * L1e 破坏性反向验证：OHOS SDK sysroot 自带系统 zlib.h/libz.so，若 test 源码只 include
 * <zlib.h>，CI 移走包产物后仍可 fallback 到系统头文件编译通过 → 误判为“假测试”。
 * 因此 conanfile.py build() 显式校验包内 include/lib 路径存在（见注释），
 * 且本源码通过 "-I<package include dir>" 精确引用被测包头文件，真实依赖被测包。
 */
#include <zlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

static int test_compress_roundtrip(void) {
    const char *src = "HarmonyOS PC zlib API roundtrip test 1234567890";
    uLongf src_len = (uLongf)strlen(src) + 1;   /* 含 NUL */
    uLongf bound = compressBound(src_len);
    unsigned char *comp = (unsigned char *)malloc(bound);
    unsigned char *decomp = (unsigned char *)malloc(src_len);
    if (!comp || !decomp) { fprintf(stderr, "FAIL: malloc\n"); return 1; }

    uLongf comp_len = bound;
    if (compress(comp, &comp_len, (const Bytef *)src, src_len) != Z_OK) {
        fprintf(stderr, "FAIL: compress\n"); return 1;
    }
    uLongf decomp_len = src_len;
    if (uncompress(decomp, &decomp_len, comp, comp_len) != Z_OK) {
        fprintf(stderr, "FAIL: uncompress\n"); return 1;
    }
    if (decomp_len != src_len || memcmp(decomp, src, src_len) != 0) {
        fprintf(stderr, "FAIL: roundtrip data mismatch\n"); return 1;
    }

    /* compress2 指定压缩级别 + uncompress2 显式输入/输出长度 */
    uLongf c2_len = bound;
    if (compress2(comp, &c2_len, (const Bytef *)src, src_len, Z_BEST_COMPRESSION) != Z_OK) {
        fprintf(stderr, "FAIL: compress2\n"); return 1;
    }
    uLongf d2_len = src_len;
    if (uncompress2(decomp, &d2_len, comp, &c2_len) != Z_OK) {
        fprintf(stderr, "FAIL: uncompress2\n"); return 1;
    }
    if (d2_len != src_len || memcmp(decomp, src, src_len) != 0) {
        fprintf(stderr, "FAIL: compress2 roundtrip mismatch\n"); return 1;
    }
    free(comp);
    free(decomp);
    return 0;
}

static int test_checksums(void) {
    const char *data = "checksum me";
    uLong a = adler32(0L, Z_NULL, 0);
    a = adler32(a, (const Bytef *)data, (uInt)strlen(data));
    if (a == 0) { fprintf(stderr, "FAIL: adler32\n"); return 1; }
    uLong c = crc32(0L, Z_NULL, 0);
    c = crc32(c, (const Bytef *)data, (uInt)strlen(data));
    if (c == 0) { fprintf(stderr, "FAIL: crc32\n"); return 1; }
    printf("adler32=0x%lx crc32=0x%lx\n", a, c);
    return 0;
}

static int test_deflate_inflate(void) {
    const char *src = "deflate/inflate stream roundtrip on HarmonyOS PC";
    uLongf src_len = (uLongf)strlen(src) + 1;
    unsigned char comp[512];
    unsigned char decomp[128];

    z_stream strm;
    memset(&strm, 0, sizeof(strm));
    if (deflateInit(&strm, Z_DEFAULT_COMPRESSION) != Z_OK) {
        fprintf(stderr, "FAIL: deflateInit\n"); return 1;
    }
    strm.next_in = (Bytef *)src;
    strm.avail_in = (uInt)src_len;
    strm.next_out = comp;
    strm.avail_out = sizeof(comp);
    if (deflate(&strm, Z_FINISH) != Z_STREAM_END) {
        fprintf(stderr, "FAIL: deflate\n"); return 1;
    }
    uLongf comp_len = (uLongf)strm.total_out;
    deflateEnd(&strm);

    memset(&strm, 0, sizeof(strm));
    if (inflateInit(&strm) != Z_OK) {
        fprintf(stderr, "FAIL: inflateInit\n"); return 1;
    }
    strm.next_in = comp;
    strm.avail_in = (uInt)comp_len;
    strm.next_out = decomp;
    strm.avail_out = sizeof(decomp);
    if (inflate(&strm, Z_FINISH) != Z_STREAM_END) {
        fprintf(stderr, "FAIL: inflate\n"); return 1;
    }
    if (strm.total_out != src_len || memcmp(decomp, src, src_len) != 0) {
        fprintf(stderr, "FAIL: inflate data mismatch\n"); return 1;
    }
    inflateEnd(&strm);
    return 0;
}

static int test_gzfile(void) {
    const char *path = "./hos_test_tmp.gz";
    const char *data = "gzip file roundtrip via gzopen/gzwrite/gzread";
    gzFile gz = gzopen(path, "wb");
    if (!gz) { fprintf(stderr, "FAIL: gzopen wb\n"); return 1; }
    if (gzwrite(gz, data, (unsigned)strlen(data)) != (int)strlen(data)) {
        fprintf(stderr, "FAIL: gzwrite\n"); gzclose(gz); return 1;
    }
    gzclose(gz);

    char buf[128];
    gz = gzopen(path, "rb");
    if (!gz) { fprintf(stderr, "FAIL: gzopen rb\n"); return 1; }
    int n = gzread(gz, buf, (unsigned)strlen(data));
    gzclose(gz);
    if (n != (int)strlen(data) || memcmp(buf, data, (size_t)n) != 0) {
        fprintf(stderr, "FAIL: gzread mismatch n=%d\n", n); return 1;
    }
    remove(path);
    return 0;
}

int main(void) {
    printf("zlib %s ok\n", zlibVersion());
    if (strcmp(zlibVersion(), "1.3.2") != 0) {
        fprintf(stderr, "FAIL: unexpected zlib version\n");
        return 1;
    }
    if (test_compress_roundtrip()) return 1;
    if (test_checksums()) return 1;
    if (test_deflate_inflate()) return 1;
    if (test_gzfile()) return 1;
    printf("PASS: zlib API smoke test (compress/uncompress, compress2/uncompress2, "
           "adler32/crc32, deflate/inflate, gzopen/gzread) OK\n");
    return 0;
}
