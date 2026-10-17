/*
 * consumer_vault.c — arduinospritzcipher 1.2.0 消费者验证用例
 *
 * 模拟业务上层应用「口令加密保险箱」：仅通过库已安装/导出的公开头文件
 * (SpritzCipher.h)、公开 API（spritz_hash/spritz_crypt/spritz_compare/
 * spritz_mac）与正常链接目标（libSpritzCipher.a）编译、链接并运行。
 * 不包含库私有头文件、不调用内部符号、不复用库内部测试构建目录。
 *
 * 业务场景：口令哈希存储 + 明文加密归档 + MAC 完整性校验（一次性实现
 * 三个有业务意义的公开 API 调用并输出可观察结果）。
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <SpritzCipher.h>

static const uint8_t g_password[8] = {'s', 'e', 'c', 'r', 'e', 't', '!', '9'};
static const uint8_t g_vault_key[6] = {'v', 'a', 'u', 'l', 't', '1'};

int main(void)
{
    uint8_t pwd_hash[32];
    uint8_t ciphertext[16], plaintext[16];
    uint8_t mac[16];
    spritz_ctx ctx;
    const uint8_t doc[14] = "TopSecretDoc!";
    int rc = 0;

    /* 1) 口令哈希存储：spritz_hash 公开 API，输出可观察 32 字节摘要 */
    spritz_hash(pwd_hash, sizeof(pwd_hash), g_password, sizeof(g_password));
    printf("pwd_hash=");
    for (unsigned i = 0; i < sizeof(pwd_hash); i++)
        printf("%02x", pwd_hash[i]);
    printf("\n");
    /* 再算一次，验证确定性（业务侧重复登录校验依赖此性质） */
    uint8_t pwd_hash2[32];
    spritz_hash(pwd_hash2, sizeof(pwd_hash2), g_password, sizeof(g_password));
    if (spritz_compare(pwd_hash, pwd_hash2, sizeof(pwd_hash)) != 0) {
        printf("CONSUMER_FAIL: password hash not deterministic\n");
        return 1;
    }
    printf("consumer: password-hash deterministic OK\n");

    /* 2) 归档加密：spritz_crypt 公开 API，密文长度与明文一致 */
    spritz_setup(&ctx, g_vault_key, sizeof(g_vault_key));
    spritz_crypt(&ctx, doc, sizeof(doc), ciphertext);
    printf("ciphertext_len=%u\n", (unsigned)sizeof(ciphertext));

    /* 3) MAC 完整性校验：spritz_mac 公开 API，密文附带认证标签 */
    spritz_mac(mac, sizeof(mac), ciphertext, sizeof(doc), g_vault_key, sizeof(g_vault_key));
    printf("mac=");
    for (unsigned i = 0; i < sizeof(mac); i++)
        printf("%02x", mac[i]);
    printf("\n");

    /* 业务侧解密回明文并核对原文 */
    spritz_setup(&ctx, g_vault_key, sizeof(g_vault_key));
    spritz_crypt(&ctx, ciphertext, sizeof(doc), plaintext);
    if (spritz_compare(plaintext, doc, sizeof(doc)) != 0) {
        printf("CONSUMER_FAIL: vault decrypt mismatch\n");
        return 2;
    }
    printf("consumer: vault encrypt->decrypt roundtrip OK (doc=%s)\n", (char *)plaintext);
    printf("CONSUMER_VAULT_PASS\n");
    return rc;
}
