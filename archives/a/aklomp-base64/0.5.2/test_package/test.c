/* test_package/test.c — aklomp-base64 消费者测试
   验证可链接 libbase64.a 并调用 base64_encode/base64_decode。
   "Hello, World!" → SGVsbG8sIFdvcmxkIQ== 往返一致即 PASS。
*/
#include <libbase64.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *plain = "Hello, World!";
    const char *expected = "SGVsbG8sIFdvcmxkIQ==";
    char enc[256];
    char dec[256];
    size_t enc_len, dec_len;

    /* API 契约：调用前 outlen 须设为缓冲区容量，返回时更新为实际长度 */
    enc_len = sizeof(enc);
    base64_encode(plain, strlen(plain), enc, &enc_len, 0);
    if (enc_len != strlen(expected) || memcmp(enc, expected, enc_len) != 0) {
        fprintf(stderr, "FAIL: encode mismatch (got %.*s)\n", (int)enc_len, enc);
        return 1;
    }
    printf("encode ok: %.*s\n", (int)enc_len, enc);

    dec_len = sizeof(dec);
    if (!base64_decode(enc, enc_len, dec, &dec_len, 0)) {
        fprintf(stderr, "FAIL: base64_decode returned 0\n");
        return 1;
    }
    if (dec_len != strlen(plain) || memcmp(dec, plain, dec_len) != 0) {
        fprintf(stderr, "FAIL: decode mismatch\n");
        return 1;
    }
    printf("decode ok: %.*s\n", (int)dec_len, dec);

    printf("base64 smoke test: PASS\n");
    return 0;
}
