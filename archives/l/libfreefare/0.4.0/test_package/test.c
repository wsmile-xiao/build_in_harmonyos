/**
 * test_libfreefare — 消费者视角验证（Conan L1）
 *
 * 只调用不依赖物理 NFC 读卡器的纯函数 / 对象生命周期 API，
 * 真实链接并执行被测库（libfreefare）：
 *   - MIFARE Classic 扇区几何换算（纯计算）
 *   - MIFARE DESFire AID 构造与读取
 *   - DES / AES key 对象分配与释放（走 libcrypto，验证 -lcrypto 链接）
 *   - MAD（Mifare Application Directory）对象构造与版本读写
 *   - TLV 编解码往返
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <freefare.h>

#define CHECK(cond) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); return 1; } \
} while (0)

int main(void)
{
    /* 1) MIFARE Classic 扇区几何（纯计算，无设备）
     *    MIFARE Classic 1K：每扇区 4 块，块 0..3 = 扇区 0。 */
    CHECK(mifare_classic_sector_block_count(0) == 4);
    CHECK(mifare_classic_sector_first_block(0) == 0);
    CHECK(mifare_classic_sector_last_block(0) == 3);
    CHECK(mifare_classic_block_sector(4) == 1);   /* 块 4 属于扇区 1 */
    CHECK(mifare_classic_block_sector(3) == 0);   /* 块 3 属于扇区 0 */

    /* 2) DESFire AID 构造/读取（不接触卡片） */
    MifareDESFireAID aid = mifare_desfire_aid_new(0x123456);
    CHECK(aid != NULL);
    CHECK(mifare_desfire_aid_get_aid(aid) == 0x123456);

    /* 3) 密钥对象分配/释放 —— 间接验证 libcrypto(DES/AES) 已正确链接 */
    uint8_t des_key[8] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
    MifareDESFireKey dk = mifare_desfire_des_key_new_with_version(des_key);
    CHECK(dk != NULL);
    mifare_desfire_key_free(dk);

    uint8_t aes_key[16] = {0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,
                           0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff};
    MifareDESFireKey ak = mifare_desfire_aes_key_new_with_version(aes_key, 0);
    CHECK(ak != NULL);
    mifare_desfire_key_free(ak);

    /* 4) MAD 对象构造/版本读写（纯内存） */
    Mad mad = mad_new(0);
    CHECK(mad != NULL);
    CHECK(mad_get_version(mad) == 0);
    mad_set_version(mad, 1);
    CHECK(mad_get_version(mad) == 1);
    mad_free(mad);

    /* 5) TLV 编解码往返 */
    const uint8_t value[3] = {0x01, 0x02, 0x03};
    size_t outlen = 0;
    uint8_t *encoded = tlv_encode(0x85, value, 3, &outlen);
    CHECK(encoded != NULL);
    /* type(1) + len(1) + value(3) + terminator 0xFE(1) = 6 */
    CHECK(outlen == 6);
    uint8_t type = 0;
    uint16_t parsed_len = 0;
    uint8_t *body = tlv_decode(encoded, &type, &parsed_len);
    CHECK(body != NULL);
    CHECK(type == 0x85);
    CHECK(parsed_len == 3);
    CHECK(memcmp(body, value, 3) == 0);
    free(encoded);
    free(body);

    /* 6) 新增消费者用例：多 DESFire AID 实例互不干扰（独立构造/读回）
     *    验证 AID 对象构造与隔离语义，纯内存无设备。
     *    注：freefare.h 未提供 mifare_desfire_aid_free（单例 AID 无显式释放 API）。 */
    MifareDESFireAID aid1 = mifare_desfire_aid_new(0xAAAAAA);
    MifareDESFireAID aid2 = mifare_desfire_aid_new(0x555555);
    CHECK(aid1 != NULL && aid2 != NULL);
    CHECK(aid1 != aid2);
    CHECK(mifare_desfire_aid_get_aid(aid1) == 0xAAAAAA);
    CHECK(mifare_desfire_aid_get_aid(aid2) == 0x555555);

    /* 7) 新增消费者用例：MIFARE Classic 1K 末扇区几何（扇区 15 = 最后扇区）
     *    Classic 1K 共 16 扇区，每扇区 4 块；扇区 15 首块 = 15*4 = 60，末块 = 63 */
    CHECK(mifare_classic_sector_block_count(15) == 4);
    CHECK(mifare_classic_sector_first_block(15) == 60);
    CHECK(mifare_classic_sector_last_block(15) == 63);
    CHECK(mifare_classic_block_sector(63) == 15);

    printf("test libfreefare 0.4.0: OK "
           "(sector-geo/aid/keys/mad/tlv/multi-aid/last-sector assertions passed)\n");
    return 0;
}
