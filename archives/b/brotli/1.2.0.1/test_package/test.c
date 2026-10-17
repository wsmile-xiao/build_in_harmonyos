/* brotli 1.2.0 —— 真实压缩/解压往返验证（非 dlopen 空壳）。
 *
 * 判据设计：
 *   ① 压缩必须真的变小 —— 用高度可压缩的重复串，压完应远小于原文；
 *      只验「函数能调通」的话，一个原样拷贝的实现也能过。
 *   ② 解压回来必须与原文逐字节相同 —— 这才证明编解码是配套且正确的。
 *   ③ 同时链 libbrotlienc 与 libbrotlidec，覆盖两个组件库
 *      （原占位测试只 dlopen 了 libbrotlidec.so，另一个根本没碰）。
 *
 * 注意头路径是 <brotli/encode.h> / <brotli/decode.h>，
 * 上游没有 <brotli.h> —— 生成器按包名猜的那个头不存在。
 */
#include <stdint.h>          /* uint8_t：brotli/types.h 不保证带进来 */
#include <brotli/decode.h>
#include <brotli/encode.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);\
            ++failures;                                                        \
        } else {                                                               \
            printf("[ok] %s\n", (msg));                                        \
        }                                                                      \
    } while (0)

int main(void) {
    /* 高度可压缩：同一段文字重复 64 次 */
    char input[64 * 32];
    size_t input_size = 0;
    for (int i = 0; i < 64; ++i) {
        memcpy(input + input_size, "harmony-pc brotli roundtrip ok! ", 32);
        input_size += 32;
    }

    uint8_t encoded[sizeof(input) * 2];
    size_t encoded_size = sizeof(encoded);
    BROTLI_BOOL enc = BrotliEncoderCompress(
        BROTLI_DEFAULT_QUALITY, BROTLI_DEFAULT_WINDOW, BROTLI_MODE_GENERIC,
        input_size, (const uint8_t *)input, &encoded_size, encoded);
    CHECK(enc == BROTLI_TRUE, "BrotliEncoderCompress 成功");
    if (enc != BROTLI_TRUE) {
        fprintf(stderr, "\nbrotli: 压缩失败，后续断言无意义\n");
        return 1;
    }

    printf("     原始 %zu 字节 → 压缩后 %zu 字节\n", input_size, encoded_size);
    /* 2048 字节的 32 字节重复串，brotli 应能压到很小；给个宽松但有意义的上限 */
    CHECK(encoded_size < input_size / 8,
          "压缩率显著（压缩后 < 原始的 1/8，证明确实在压而非原样拷贝）");

    uint8_t decoded[sizeof(input)];
    size_t decoded_size = sizeof(decoded);
    BrotliDecoderResult dec = BrotliDecoderDecompress(
        encoded_size, encoded, &decoded_size, decoded);
    CHECK(dec == BROTLI_DECODER_RESULT_SUCCESS, "BrotliDecoderDecompress 成功");
    CHECK(decoded_size == input_size, "解压后长度与原文一致");
    if (decoded_size == input_size) {
        CHECK(memcmp(decoded, input, input_size) == 0, "解压内容与原文逐字节相同");
    }

    if (failures) {
        fprintf(stderr, "\nbrotli: %d 项断言失败\n", failures);
        return 1;
    }
    printf("\nbrotli 1.2.0: 全部断言通过（enc+dec 往返）\n");
    return 0;
}
