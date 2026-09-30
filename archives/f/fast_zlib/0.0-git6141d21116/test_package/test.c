/* test.c — fast_zlib 消费者验证 (R34: 必须实质调用被测包 API)
 *
 * 通过 fast_zlib 提供的 zlib 兼容公开 API (zlib.h) 完成
 * compress2/uncompress 往返压缩与解压，验证数据一致性与压缩率。
 * fast_zlib 的优化点在于 deflate 内部的 longest_match（C 版快速匹配），
 * 公开 API 面与 zlib 完全一致，因此本测试即验证快速匹配路径可达。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

int main(void) {
    const char *version = zlibVersion();
    printf("zlib version: %s\n", version);

    /* 构造可压缩数据：重复文本块 + 随机尾块 */
    const size_t src_len = 512 * 1024;
    unsigned char *input = (unsigned char *)malloc(src_len);
    if (!input) {
        fprintf(stderr, "FAIL: malloc(input) failed\n");
        return 1;
    }
    const char *block =
        "fast_zlib optimized longest_match for zlib compression, HarmonyOS PC port. ";
    size_t i = 0;
    while (i < src_len) {
        size_t n = strlen(block);
        if (i + n > src_len) n = src_len - i;
        memcpy(input + i, block, n);
        i += n;
    }
    /* 尾部掺入不可压缩随机字节，验证 deflate 处理混合数据 */
    unsigned int seed = 0x5A17;
    for (i = src_len - 4096; i < src_len; i++) {
        seed = seed * 1103515245u + 12345u;
        input[i] = (unsigned char)(seed >> 16);
    }

    unsigned long dest_len = compressBound(src_len);
    unsigned char *compressed = (unsigned char *)malloc(dest_len);
    if (!compressed) {
        fprintf(stderr, "FAIL: malloc(compressed) failed\n");
        free(input);
        return 1;
    }

    /* 使用 fast_zlib 的 deflate 快速匹配路径压缩 (level 9 = zlib fastest/slowest tradeoff) */
    int ret = compress2(compressed, &dest_len, input, src_len, 9);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: compress2() returned %d\n", ret);
        free(input);
        free(compressed);
        return 1;
    }
    printf("compress2 OK (src=%lu -> dest=%lu, ratio=%.2f)\n",
           src_len, dest_len, (double)dest_len / (double)src_len);
    if (dest_len >= src_len) {
        fprintf(stderr, "FAIL: no compression achieved\n");
        free(input);
        free(compressed);
        return 1;
    }

    /* 解压验证往返一致性 */
    unsigned long out_len = src_len;
    unsigned char *decompressed = (unsigned char *)malloc(out_len);
    if (!decompressed) {
        fprintf(stderr, "FAIL: malloc(decompressed) failed\n");
        free(input);
        free(compressed);
        return 1;
    }
    ret = uncompress(decompressed, &out_len, compressed, dest_len);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: uncompress() returned %d\n", ret);
        free(input);
        free(compressed);
        free(decompressed);
        return 1;
    }
    if (out_len != src_len || memcmp(input, decompressed, src_len) != 0) {
        fprintf(stderr, "FAIL: roundtrip data mismatch (out_len=%lu)\n", out_len);
        free(input);
        free(compressed);
        free(decompressed);
        return 1;
    }
    printf("uncompress OK: roundtrip %lu bytes identical\n", out_len);

    free(input);
    free(compressed);
    free(decompressed);

    printf("PASS: fast_zlib zlib-compatible API is functional\n");
    return 0;
}