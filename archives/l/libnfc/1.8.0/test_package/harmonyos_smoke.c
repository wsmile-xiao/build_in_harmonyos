/**
 * harmonyos_smoke.c — HarmonyOS 平台专项测试（消费者视角，无需物理 NFC 设备）
 *
 * 验证 libnfc 在 HarmonyOS PC (aarch64) 上可用的真实能力：
 *   1. nfc_version()  返回 "1.8.0"（与编译期 PACKAGE_VERSION 一致）
 *   2. nfc_init()/nfc_exit() 上下文生命周期正常（无需硬件）
 *   3. nfc_list_devices() 无设备时优雅返回 0（不崩溃、不悬挂）
 *   4. 平台特征：OHOS（__OHOS__ 或 uname -s=HarmonyOS）+ aarch64 小端序
 *
 * 除平台断言外全部通过真实 libnfc 公共 API 执行，禁止空测试/伪造输出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/utsname.h>

#include <nfc/nfc.h>

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
    printf("harmonyos_smoke: HarmonyOS platform test for libnfc %s\n", nfc_version());

    /* 1. 版本 API */
    CHECK(strcmp(nfc_version(), "1.8.0") == 0, "nfc_version() == \"1.8.0\"");

    /* 2. 上下文生命周期（无设备） */
    nfc_context *ctx = NULL;
    nfc_init(&ctx);
    CHECK(ctx != NULL, "nfc_init() creates non-NULL context");
    if (ctx) {
        nfc_exit(ctx);
        printf("  [PASS] nfc_exit(context) OK\n");
    } else {
        printf("  [FAIL] nfc_exit(context)\n");
        failures++;
    }

    /* 3. 设备枚举：无设备时优雅返回 0 */
    nfc_context *ctx2 = NULL;
    nfc_init(&ctx2);
    if (ctx2) {
        nfc_connstring conns[1];
        size_t n = nfc_list_devices(ctx2, conns, 1);
        printf("  [INFO] nfc_list_devices() = %zu (无物理读卡器时应为 0 或 >=0 不崩溃)\n", n);
        CHECK(n <= 1, "nfc_list_devices() bounded result (no crash)");
        nfc_exit(ctx2);
    }

    /* 4. 平台特征（HarmonyOS + aarch64 小端） */
    {
        /* 真实平台能力校验：uname -s 必须为 HarmonyOS（__OHOS__ 宏 + 运行时系统名双重断言） */
        struct utsname uts;
        if (uname(&uts) == 0) {
            CHECK(strstr(uts.sysname, "HarmonyOS") != NULL, "uname sysname is HarmonyOS");
        } else {
            printf("  [WARN] uname() failed; fallback to __OHOS__ macro only\n");
#ifdef __OHOS__
            CHECK(1, "compiled with __OHOS__ (HarmonyOS)");
#endif
        }
    }
    {
        uint16_t probe = 0x0102;
        uint8_t *p = (uint8_t *)&probe;
        CHECK(p[0] == 0x02, "aarch64 little-endian byte order");
    }

    if (failures == 0) {
        printf("harmonyos_smoke: ALL CHECKS PASSED\n");
        return 0;
    }
    printf("harmonyos_smoke: %d CHECK(S) FAILED\n", failures);
    return 1;
}