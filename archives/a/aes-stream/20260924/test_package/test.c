/* 消费者测试：仅通过官方公开头 aes-stream.h + 已安装库使用公开 API。
 * 断言：
 *   1) 固定 seed 的已知答案（与已验证标量参考/AES-NI 构造 bit-exact 一致）
 *   2) 确定性：同一 seed 重新初始化输出一致
 *   3) 非全零输出
 *   4) key-erasure 后继续调用仍产生有效输出
 */
#include <aes-stream.h>
#include <stdio.h>
#include <string.h>

static int hex_equal(const unsigned char *p, const char *hex, int n) {
    for (int i = 0; i < n; i++) {
        unsigned v;
        sscanf(hex + 2 * i, "%2x", &v);
        if (p[i] != (unsigned char) v) {
            printf("byte %d: got %02x want %s\n", i, p[i], hex + 2 * i);
            return 0;
        }
    }
    return 1;
}

int main(void) {
    unsigned char seed[AES_STREAM_SEEDBYTES];
    unsigned char buf[64], buf2[64];
    for (int i = 0; i < 32; i++) seed[i] = (unsigned char) i;

    aes_stream_state st;
    aes_stream_init(&st, seed);
    aes_stream(&st, buf, sizeof buf);

    /* KAT：seed=000102..1f, AES-128 首 64 字节（由已验证参考实现生成）*/
    const char *expected =
        "fd517c4f759de5c8be455b191ef7785c"
        "af62fc2893f76ea6f3343f0659e2fad0"
        "8622848fc59353d4241af59aded1b3255"
        "328b374ac6267b76d8f19670f704fab";
    if (!hex_equal(buf, expected, 64)) {
        printf("FAIL: known-answer mismatch\n");
        return 1;
    }
    printf("PASS: known-answer (first 64 bytes) matches reference\n");

    /* 确定性 */
    aes_stream_init(&st, seed);
    aes_stream(&st, buf2, sizeof buf2);
    if (memcmp(buf, buf2, sizeof buf) != 0) {
        printf("FAIL: determinism\n");
        return 1;
    }
    printf("PASS: deterministic output for same seed\n");

    /* 非全零 */
    int nonzero = 0;
    for (int i = 0; i < 64; i++) if (buf[i] != 0) nonzero++;
    if (nonzero == 0) {
        printf("FAIL: all-zero output\n");
        return 1;
    }
    printf("PASS: %d/64 nonzero bytes\n", nonzero);

    /* key erasure 后继续调用仍产生有效输出（同一 st 不重新初始化）*/
    aes_stream(&st, buf2, sizeof buf2);
    nonzero = 0;
    for (int i = 0; i < 64; i++) if (buf2[i] != 0) nonzero++;
    if (nonzero == 0) {
        printf("FAIL: post-erasure output all zero\n");
        return 1;
    }
    printf("PASS: post-key-erasure stream continues (%d/64 nonzero)\n", nonzero);

    printf("ALL TEST_PACKAGE CHECKS PASSED\n");
    return 0;
}