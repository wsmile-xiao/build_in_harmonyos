/*
 * HarmonyOS PC 特有测试 — tiny-aes-c 1.0.0
 *
 * 本测试验证本库在鸿蒙 PC 平台特有的行为（规则 12 整改新增，非上游测试重复）：
 *
 *   1. E002 /tmp 只读：鸿蒙 PC 上对 /tmp 的写入必须失败（EROFS），应用必须改用
 *      $TMPDIR / $HOME/tmp；本测试先探测 /tmp 只读属性，确认平台行为。
 *   2. $TMPDIR / $HOME/tmp 可写临时目录（HMDFS 真实文件 I/O）：作为加密数据
 *      落盘路径，验证鸿蒙平台上临时目录的读写能力。
 *   3. AES-CBC 加密 -> 密文落盘 -> 重新读取 -> 解密 round-trip：密文逐字节
 *      还原为明文，证明库在鸿蒙平台真实文件 I/O 下的加解密往返完整性；
 *      同时断言密文与 NIST SP 800-38A F.2.1 CBC-AES128 向量一致。
 *
 * 测试实际调用被测包 aes.h API（AES_init_ctx_iv / AES_CBC_encrypt_buffer /
 * AES_CBC_decrypt_buffer），通过 test_package 链接 libtiny-aes.a。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>

#define CBC 1
#include "aes.h"

#define KEY_BYTES 16
#define IV_BYTES  16
#define PLAIN_LEN 64 /* 4 个 AES 块 */

/* NIST SP 800-38A F.2.1 CBC-AES128 密钥 / 初始向量 */
static const uint8_t nist_key[KEY_BYTES] = {
    0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
    0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c
};
static const uint8_t nist_iv[IV_BYTES] = {
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
    0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
};
/* NIST SP 800-38A F.2.1 CBC-AES128 明文（4 块） */
static const uint8_t nist_plain[PLAIN_LEN] = {
    0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
    0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a,
    0xae, 0x2d, 0x8a, 0x57, 0x1e, 0x03, 0xac, 0x9c,
    0x9e, 0xb7, 0x6f, 0xac, 0x45, 0xaf, 0x8e, 0x51,
    0x30, 0xc8, 0x1c, 0x46, 0xa3, 0x5c, 0xe4, 0x11,
    0xe5, 0xfb, 0xc1, 0x19, 0x1a, 0x0a, 0x52, 0xef,
    0xf6, 0x9f, 0x24, 0x45, 0xdf, 0x4f, 0x9b, 0x17,
    0xad, 0x2b, 0x41, 0x7b, 0xe6, 0x6c, 0x37, 0x10
};
/* NIST SP 800-38A F.2.1 CBC-AES128 密文（期望输出） */
static const uint8_t nist_cipher[PLAIN_LEN] = {
    0x76, 0x49, 0xab, 0xac, 0x81, 0x19, 0xb2, 0x46,
    0xce, 0xe9, 0x8e, 0x9b, 0x12, 0xe9, 0x19, 0x7d,
    0x50, 0x86, 0xcb, 0x9b, 0x50, 0x72, 0x19, 0xee,
    0x95, 0xdb, 0x11, 0x3a, 0x91, 0x76, 0x78, 0xb2,
    0x73, 0xbe, 0xd6, 0xb8, 0xe3, 0xc1, 0x74, 0x3b,
    0x71, 0x16, 0xe6, 0x9e, 0x22, 0x22, 0x95, 0x16,
    0x3f, 0xf1, 0xca, 0xa1, 0x68, 0x1f, 0xac, 0x09,
    0x12, 0x0e, 0xca, 0x30, 0x75, 0x86, 0xe1, 0xa7
};

static int failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (cond) {                                                         \
            printf("PASS: %s\n", msg);                                      \
        } else {                                                            \
            printf("FAIL: %s\n", msg);                                      \
            failures++;                                                     \
        }                                                                   \
    } while (0)

int main(void)
{
    char tmpdir[512];
    char path[640];
    const char *env;
    uint8_t plain[PLAIN_LEN];
    uint8_t cipher[PLAIN_LEN];
    uint8_t back[PLAIN_LEN];
    struct AES_ctx ctx;
    FILE *f;
    size_t got;

    printf("== tiny-aes-c 1.0.0 HarmonyOS PC specific test ==\n");

    /* --- 1. E002：/tmp 只读探测（鸿蒙 PC 平台行为） --- */
    f = fopen("/tmp/.ohos_tinyaes_probe", "w");
    if (f != NULL) {
        fclose(f);
        remove("/tmp/.ohos_tinyaes_probe");
        CHECK(0, "E002: /tmp is read-only on HarmonyOS PC (write must fail)");
        printf("INFO: /tmp write unexpectedly succeeded (non-OHOS variant?)\n");
    } else {
        CHECK(errno == EROFS || errno == EACCES || errno == EPERM,
              "E002: /tmp is read-only on HarmonyOS PC (write rejected)");
        printf("INFO: /tmp probe errno=%d (%s)\n", errno, strerror(errno));
    }

    /* --- 2. 解析鸿蒙平台可写临时目录：$TMPDIR -> $HOME/tmp --- */
    env = getenv("TMPDIR");
    if (env != NULL && env[0] != '\0') {
        snprintf(tmpdir, sizeof(tmpdir), "%s", env);
    } else {
        env = getenv("HOME");
        if (env == NULL || env[0] == '\0') {
            snprintf(tmpdir, sizeof(tmpdir), "/tmp");
        } else {
            snprintf(tmpdir, sizeof(tmpdir), "%s/tmp", env);
        }
    }
    if (mkdir(tmpdir, 0700) != 0 && errno != EEXIST) {
        /* 目录已存在视为成功；HMDFS 下 chmod 可能被忽略（E046），不阻塞 */
        if (errno != EEXIST) {
            CHECK(0, "temp dir accessible");
        }
    }
    snprintf(path, sizeof(path), "%s/.ohos_tinyaes_probe", tmpdir);
    f = fopen(path, "w");
    if (f != NULL) {
        fclose(f);
        remove(path);
        CHECK(1, "temp dir writable (used for encrypted payload persistence)");
    } else {
        CHECK(0, "temp dir writable (used for encrypted payload persistence)");
    }
    printf("INFO: temp dir = %s (HarmonyOS temp convention: TMPDIR/HOME/tmp)\n", tmpdir);

    /* --- 3. AES-CBC 加密 -> 落盘 -> 重读 -> 解密 round-trip --- */
    memcpy(plain, nist_plain, PLAIN_LEN);
    AES_init_ctx_iv(&ctx, nist_key, nist_iv);
    memcpy(cipher, plain, PLAIN_LEN);
    AES_CBC_encrypt_buffer(&ctx, cipher, PLAIN_LEN);

    CHECK(memcmp(cipher, nist_cipher, PLAIN_LEN) == 0,
          "AES-CBC ciphertext matches NIST SP 800-38A F.2.1 vector");
    CHECK(memcmp(cipher, plain, PLAIN_LEN) != 0,
          "ciphertext differs from plaintext (real encryption happened)");

    snprintf(path, sizeof(path), "%s/tinyaes_roundtrip_%d.bin",
             tmpdir, (int)getpid());
    f = fopen(path, "wb");
    CHECK(f != NULL, "open temp file for ciphertext write");
    if (f != NULL) {
        fwrite(cipher, 1, PLAIN_LEN, f);
        fclose(f);
    }
    memset(back, 0, sizeof(back));
    f = fopen(path, "rb");
    CHECK(f != NULL, "re-open temp file for ciphertext read-back");
    if (f != NULL) {
        got = fread(back, 1, PLAIN_LEN, f);
        fclose(f);
        CHECK(got == PLAIN_LEN, "read back full ciphertext from disk");
    }
    remove(path);
    CHECK(memcmp(back, cipher, PLAIN_LEN) == 0,
          "disk round-trip: ciphertext read back byte-identical");

    AES_init_ctx_iv(&ctx, nist_key, nist_iv);
    AES_CBC_decrypt_buffer(&ctx, back, PLAIN_LEN);
    CHECK(memcmp(back, plain, PLAIN_LEN) == 0,
          "decrypt after disk round-trip recovers plaintext exactly");

    if (failures == 0) {
        printf("== HarmonyOS features verified: E002 /tmp read-only, "
               "TMPDIR/HOME/tmp writable temp FS, AES-CBC disk round-trip "
               "integrity ==\n");
        printf("tiny-aes-c 1.0.0 harmony test: ALL CHECKS PASSED\n");
    } else {
        printf("tiny-aes-c 1.0.0 harmony test: %d check(s) FAILED\n", failures);
    }
    return failures == 0 ? 0 : 1;
}
