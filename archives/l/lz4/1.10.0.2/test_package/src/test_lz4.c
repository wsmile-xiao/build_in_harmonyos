// test_lz4.c — 消费者用例：模拟上层组件调用 LZ4 公开 API
//
// 验证：
//   1. lz4.h 可包含（公开头）
//   2. 链接 liblz4.a 成功
//   3. 调用跑通：LZ4_compress_default → LZ4_decompress_safe 往返，
//      解压结果与原文一致（真实功能验证，非占位）
#include <lz4.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void)
{
    /* 断言 1：版本 API 可用且匹配 */
    CHECK(LZ4_versionNumber() >= 11000);
    const char *ver = LZ4_versionString();
    CHECK(ver != NULL);

    /* 断言 2：压缩-解压往返正确（真实功能） */
    const char *src = "The quick brown fox jumps over the lazy dog. "
                      "LZ4 is an extremely fast compression algorithm. "
                      "This payload repeats enough to compress well: "
                      "compress compress compress compress compress.";
    size_t src_len = strlen(src) + 1;

    int bound = LZ4_compressBound((int)src_len);
    CHECK(bound > 0);
    char *compressed = malloc((size_t)bound);
    char *decompressed = malloc(src_len);
    CHECK(compressed && decompressed);

    int csize = LZ4_compress_default(src, compressed, (int)src_len, bound);
    CHECK(csize > 0 && csize < (int)src_len);   // 有实际压缩且更小

    int dsize = LZ4_decompress_safe(compressed, decompressed,
                                    csize, (int)src_len);
    CHECK(dsize == (int)src_len);
    CHECK(memcmp(src, decompressed, src_len) == 0);

    free(compressed);
    free(decompressed);

    printf("test_lz4: OK (version=%s, src=%zu -> comp=%d, roundtrip matched)\n",
           ver, src_len, csize);
    return 0;
}
