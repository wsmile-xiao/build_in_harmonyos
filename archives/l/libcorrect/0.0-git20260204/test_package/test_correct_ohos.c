/* test_package/test_correct_ohos.c — libcorrect/0.0-git20260204 鸿蒙特有测试 (rule12)
 *
 * 验证 libcorrect Conan 包产物在 HarmonyOS PC (aarch64) 真实运行时上可用：
 *   [R1] OHOS musl 运行时：/lib/ld-musl-aarch64.so.1 存在（本测试二进制自身
 *        就由它加载，此处显式断言固化为可读证据）
 *   [R2] OHOS PC 平台：uname().machine = "aarch64" 且 LP64
 *        （sizeof(void*) = 8，与 musl ELF64 加载器一致）
 *   [R3] 真实业务流：独立于 test_correct.c 的参数组合——
 *        RS(255,239) 16 根 + 注入 4 字节损伤（t=8 > 4）、卷积码 rate 1/3
 *        order 6 + 100 字节消息——证明包产物在 OHOS 运行时上真实可执行
 *        （musl 内存语义、aarch64 指令集）
 * 任一断言失败 → 非零退出；无 skip、无静默通过。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/utsname.h>

#include <correct.h>

static int fail(const char *what)
{
    fprintf(stderr, "[test_correct_ohos] FAIL: %s\n", what);
    return 1;
}

int main(void)
{
    /* [R1] OHOS musl 动态加载器存在 */
    if (access("/lib/ld-musl-aarch64.so.1", F_OK))
        return fail("OHOS musl loader /lib/ld-musl-aarch64.so.1 not accessible");

    /* [R2] OHOS PC 平台断言 */
    struct utsname un;
    if (uname(&un)) return fail("uname failed");
    if (strcmp(un.machine, "aarch64")) {
        fprintf(stderr, "[test_correct_ohos] FAIL: uname.machine='%s'\n", un.machine);
        return 1;
    }
    if (sizeof(void *) != 8) return fail("LP64 expected");

    srand(14773);

    /* [R3a] RS(255,239) 16 roots, primitive poly 0x11d,
     * corrupt 4 bytes (t = 8 correctable) */
    correct_reed_solomon *rs = correct_reed_solomon_create(
        correct_rs_primitive_polynomial_8_4_3_2_0, 1, 1, 16);
    if (!rs) return fail("rs create (255,239) returned NULL");

    uint8_t msg[239], encoded[255], decoded[239];
    for (size_t i = 0; i < sizeof(msg); i++) msg[i] = (uint8_t)(rand() % 256);

    ssize_t enc_len = correct_reed_solomon_encode(rs, msg, sizeof(msg), encoded);
    if (enc_len != (ssize_t)sizeof(encoded)) {
        fprintf(stderr, "FAIL rs encode %zd\n", enc_len);
        return 1;
    }
    encoded[3] ^= 0xA5;
    encoded[120] ^= 0x5A;
    encoded[200] ^= 0xFF;
    encoded[254] ^= 0x01;
    ssize_t dec_len = correct_reed_solomon_decode(rs, encoded, sizeof(encoded), decoded);
    if (dec_len != (ssize_t)sizeof(msg) || memcmp(msg, decoded, sizeof(msg)) != 0) {
        fprintf(stderr, "FAIL rs decode %zd\n", dec_len);
        return 1;
    }
    correct_reed_solomon_destroy(rs);

    /* [R3b] convolutional rate 1/3 order 6 roundtrip, 100-byte message */
    correct_convolutional *conv = correct_convolutional_create(
        3, 6, correct_conv_r13_6_polynomial);
    if (!conv) return fail("conv create (1/3, K=6) returned NULL");

    uint8_t cmsg[100];
    for (size_t i = 0; i < sizeof(cmsg); i++) cmsg[i] = (uint8_t)(rand() % 256);

    size_t bits = correct_convolutional_encode_len(conv, sizeof(cmsg));
    size_t bytes = bits / 8 + ((bits % 8) ? 1 : 0);
    uint8_t *enc = calloc(bytes, 1);
    uint8_t *dec = calloc(sizeof(cmsg) + 8, 1);
    if (!enc || !dec) return fail("oom");

    size_t wbits = correct_convolutional_encode(conv, cmsg, sizeof(cmsg), enc);
    if (wbits != bits) {
        fprintf(stderr, "FAIL conv encode %zu != %zu\n", wbits, bits);
        return 1;
    }
    ssize_t dlen = correct_convolutional_decode(conv, enc, bits, dec);
    if (dlen != (ssize_t)sizeof(cmsg) || memcmp(cmsg, dec, sizeof(cmsg)) != 0) {
        fprintf(stderr, "FAIL conv decode %zd\n", dlen);
        return 1;
    }
    free(enc);
    free(dec);
    correct_convolutional_destroy(conv);

    printf("PASS: OHOS runtime asserts + RS(255,239,16) + conv(1/3,K=6) roundtrip\n");
    return 0;
}
