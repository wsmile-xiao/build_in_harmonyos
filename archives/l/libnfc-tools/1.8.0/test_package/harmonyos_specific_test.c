/*
 * HarmonyOS-specific test for libnfc-tools 1.8.0
 *
 * 本测试只做「平台特有」断言，与被测包（application 型工具集）的
 * 通用冒烟测试（run_nfc_tools_test.sh）互补：
 *   1. 编译期硬绑定鸿蒙工具链（__OHOS__ / __aarch64__）
 *   2. 运行时链接 libnfc 并调用 nfc_version()（纯函数，无需 NFC 硬件），
 *      验证依赖库 ABI 在鸿蒙 musl 上可用且版本号正确
 *   3. 校验 NFC_EXPORT 可见性宏（鸿蒙 PC 要求默认可见性导出）
 *
 * 由 test_package/conanfile.py 编译并执行。
 */

#include <stdio.h>
#include <string.h>

/* 必须先包含平台判定，编译期即绑定鸿蒙工具链 */
#if !defined(__OHOS__)
#error "HarmonyOS-specific test must be compiled by the OHOS toolchain"
#endif
#if !defined(__aarch64__)
#error "HarmonyOS PC package must target AArch64"
#endif

/* libnfc 公开接口 */
#include <nfc/nfc.h>

#define CHECK(expr) do {                                      \
    if (!(expr)) {                                            \
        fprintf(stderr, "OHOS CHECK failed at %s:%d: %s\n",   \
                __FILE__, __LINE__, #expr);                   \
        return 1;                                             \
    }                                                         \
} while (0)

int main(void)
{
    const char *ver = nfc_version();

    /* 1. nfc_version() 必须返回非空版本串 */
    CHECK(ver != NULL);

    /* 2. 版本串必须包含被测包对应的 libnfc 版本 1.8.0 */
    CHECK(strstr(ver, "1.8.0") != NULL);

    /* 3. NFC_EXPORT 可见性宏已定义（鸿蒙 PC 要求默认可见性导出） */
#if !defined(NFC_EXPORT)
#error "NFC_EXPORT visibility macro not defined"
#endif

    printf("HarmonyOS-specific libnfc ABI test passed: nfc_version()=%s\n", ver);
    return 0;
}
