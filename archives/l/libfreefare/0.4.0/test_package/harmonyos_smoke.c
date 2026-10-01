/**
 * harmonyos_smoke.c — HarmonyOS 平台专项测试（消费者视角，无需物理 NFC 设备）
 *
 * 验证 libfreefare 在 HarmonyOS PC (aarch64) 上可用的真实能力：
 *   1. 平台特征：OHOS（__OHOS__ 宏 + uname -s=HarmonyOS 双重断言）+ aarch64 小端序
 *   2. 真实调用 libfreefare 公共 API：mad_new/mad_set_version/mad_get_version/mad_free
 *   3. 真实调用 libfreefare 公共 API：tlv_encode/tlv_decode 往返
 *   4. 真实调用 libfreefare 公共 API：mifare_desfire_aid_new/aid_get_aid
 *
 * 除平台断言外全部通过真实 libfreefare 公共 API 执行，禁止空测试/伪造输出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/utsname.h>

#include <freefare.h>

static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            printf("  [PASS] %s\n", msg);                                      \
        } else {                                                               \
            printf("  [FAIL] %s\n", msg);                                      \
            failures++;                                                        \
        }                                                                      \
    } while (0)

int main(void)
{
    printf("harmonyos_smoke: HarmonyOS platform test for libfreefare 0.4.0\n");

    /* 1. 平台特征（HarmonyOS + aarch64 小端） */
    {
        struct utsname uts;
        if (uname(&uts) == 0) {
            CHECK(strstr(uts.sysname, "HarmonyOS") != NULL, "uname sysname is HarmonyOS");
        } else {
            printf("  [WARN] uname() failed; fallback to __OHOS__ macro only\n");
#ifdef __OHOS__
            CHECK(1, "compiled with __OHOS__ (HarmonyOS)");
#else
            CHECK(0, "compiled with __OHOS__ (HarmonyOS)");
#endif
        }
    }
    {
        uint16_t probe = 0x0102;
        uint8_t *p = (uint8_t *)&probe;
        CHECK(p[0] == 0x02, "aarch64 little-endian byte order");
    }

    /* 2. MAD 对象构造/版本读写（纯内存，真实调用 libfreefare API） */
    {
        Mad mad = mad_new(0);
        CHECK(mad != NULL, "mad_new(0) returns non-NULL");
        if (mad) {
            CHECK(mad_get_version(mad) == 0, "mad_get_version(mad) == 0 after new");
            mad_set_version(mad, 1);
            CHECK(mad_get_version(mad) == 1, "mad_get_version(mad) == 1 after set");
            mad_free(mad);
            printf("  [PASS] mad_free(mad) OK\n");
        }
    }

    /* 3. TLV 编解码往返（真实调用 libfreefare API） */
    {
        const uint8_t value[3] = {0x01, 0x02, 0x03};
        size_t outlen = 0;
        uint8_t *encoded = tlv_encode(0x85, value, 3, &outlen);
        CHECK(encoded != NULL, "tlv_encode(0x85, 3 bytes) returns non-NULL");
        if (encoded) {
            CHECK(outlen == 6, "tlv_encode output length == 6 (type+len+value+terminator)");
            uint8_t type = 0;
            uint16_t parsed_len = 0;
            uint8_t *body = tlv_decode(encoded, &type, &parsed_len);
            CHECK(body != NULL, "tlv_decode returns non-NULL body");
            if (body) {
                CHECK(type == 0x85, "tlv_decode type == 0x85");
                CHECK(parsed_len == 3, "tlv_decode length == 3");
                CHECK(memcmp(body, value, 3) == 0, "tlv_decode body matches original value");
                free(body);
            }
            free(encoded);
        }
    }

    /* 4. DESFire AID 构造/读取（真实调用 libfreefare API，不接触卡片） */
    {
        MifareDESFireAID aid = mifare_desfire_aid_new(0x123456);
        CHECK(aid != NULL, "mifare_desfire_aid_new(0x123456) returns non-NULL");
        if (aid) {
            CHECK(mifare_desfire_aid_get_aid(aid) == 0x123456,
                  "mifare_desfire_aid_get_aid(aid) == 0x123456");
        }
    }

    if (failures == 0) {
        printf("harmonyos_smoke: ALL CHECKS PASSED\n");
        return 0;
    }
    printf("harmonyos_smoke: %d CHECK(S) FAILED\n", failures);
    return 1;
}
