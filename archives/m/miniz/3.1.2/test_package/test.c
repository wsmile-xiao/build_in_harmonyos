/*
 * test_package consumer test — miniz 3.1.2
 * 实质验证 miniz 压缩/解压能力（zlib-compatible API，带 mz_ 前缀）。
 *
 * 覆盖:
 *   mz_compressBound / mz_compress / mz_uncompress  (压缩往返)
 *   mz_adler32 / mz_crc32                           (校验和)
 *   mz_version                                      (版本一致性)
 *
 * 链接 Conan 包内 libminiz.a（miniz::miniz），非宿主 zlib。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <miniz.h>

int main(void) {
    int failures = 0;

    /* 1. 准备一段含可压缩模式的原数据 */
    static const char src_text[] =
        "miniz is a lossless, high performance data compression library in a "
        "single source file. miniz is a lossless, high performance data "
        "compression library in a single source file. miniz is a lossless, "
        "high performance data compression library in a single source file. ";
    const mz_ulong src_len = (mz_ulong)sizeof(src_text) - 1;

    /* 2. 版本一致性
     * mz_version() 返回上游 MZ_VERSION 宏字符串（zlib 兼容版本号），
     * miniz 3.1.2 源码中 #define MZ_VERSION "11.3.2"。
     * 宿主 zlib 的 zlibVersion() 会返回 "1.2.x"，因此断言 "11.3.2"
     * 即证明链接的是 Conan 包内 miniz，而非宿主 zlib（需求 #7）。 */
    const char *ver = mz_version();
    if (!ver || strncmp(ver, "11.3.2", 6) != 0) {
        printf("FAIL: mz_version()='%s' (expected 11.3.2 = MZ_VERSION for miniz 3.1.2)\n",
               ver ? ver : "(null)");
        failures++;
        return 1; /* 版本不对，后续无意义 */
    }
    printf("[ok] mz_version() = %s (miniz 3.1.2 MZ_VERSION)\n", ver);

    /* 3. 计算压缩缓冲上界 */
    mz_ulong bound = mz_compressBound(src_len);
    if (bound <= src_len) {
        printf("FAIL: mz_compressBound(%lu)=%lu (must be > src_len)\n",
               (unsigned long)src_len, (unsigned long)bound);
        failures++;
        return 1;
    }
    printf("[ok] mz_compressBound(%lu) = %lu\n",
           (unsigned long)src_len, (unsigned long)bound);

    /* 4. 压缩 */
    unsigned char *comp = (unsigned char *)malloc((size_t)bound);
    if (!comp) {
        printf("FAIL: malloc compressed buffer\n");
        return 1;
    }
    mz_ulong comp_len = bound;
    int rc = mz_compress(comp, &comp_len, (const unsigned char *)src_text, src_len);
    if (rc != MZ_OK) {
        printf("FAIL: mz_compress rc=%d\n", rc);
        free(comp);
        return 1;
    }
    printf("[ok] mz_compress: %lu -> %lu bytes (%.1f%%)\n",
           (unsigned long)src_len, (unsigned long)comp_len,
           100.0 * comp_len / src_len);

    /* 5. 解压 */
    unsigned char *decomp = (unsigned char *)malloc((size_t)src_len + 1);
    if (!decomp) {
        printf("FAIL: malloc decompressed buffer\n");
        free(comp);
        return 1;
    }
    mz_ulong decomp_len = src_len;
    rc = mz_uncompress(decomp, &decomp_len, comp, comp_len);
    if (rc != MZ_OK) {
        printf("FAIL: mz_uncompress rc=%d\n", rc);
        free(comp);
        free(decomp);
        return 1;
    }
    printf("[ok] mz_uncompress: %lu bytes recovered\n", (unsigned long)decomp_len);

    /* 6. 验证解压结果与原数据完全一致 */
    if (decomp_len != src_len) {
        printf("FAIL: length mismatch: %lu != %lu\n",
               (unsigned long)decomp_len, (unsigned long)src_len);
        failures++;
    } else if (memcmp(decomp, src_text, (size_t)src_len) != 0) {
        printf("FAIL: data mismatch after decompress\n");
        failures++;
    } else {
        printf("[ok] decompressed data matches original exactly\n");
    }

    /* 7. 校验和一致性（原数据与解压数据的 adler32/crc32 应相同） */
    mz_ulong adler_src = mz_adler32(mz_adler32(0, NULL, 0),
                                    (const unsigned char *)src_text, (size_t)src_len);
    mz_ulong adler_dec = mz_adler32(mz_adler32(0, NULL, 0),
                                    decomp, (size_t)decomp_len);
    mz_ulong crc_src = mz_crc32(mz_crc32(0, NULL, 0),
                                (const unsigned char *)src_text, (size_t)src_len);
    mz_ulong crc_dec = mz_crc32(mz_crc32(0, NULL, 0),
                                decomp, (size_t)decomp_len);
    if (adler_src != adler_dec) {
        printf("FAIL: adler32 mismatch: %lu != %lu\n",
               (unsigned long)adler_src, (unsigned long)adler_dec);
        failures++;
    } else {
        printf("[ok] adler32 consistent: %lu\n", (unsigned long)adler_src);
    }
    if (crc_src != crc_dec) {
        printf("FAIL: crc32 mismatch: %lu != %lu\n",
               (unsigned long)crc_src, (unsigned long)crc_dec);
        failures++;
    } else {
        printf("[ok] crc32 consistent: %lu\n", (unsigned long)crc_src);
    }

    free(comp);
    free(decomp);

    if (failures == 0) {
        printf("test miniz 3.1.2: OK (compress/uncompress roundtrip + checksums)\n");
        return 0;
    }
    return 1;
}
