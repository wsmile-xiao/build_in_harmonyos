/*
 * test_ohos.c — libcec 7.1.1 HarmonyOS 专项测试
 *
 * 针对 OHOS 平台的适配验证（与上游测试、消费者用例分别计数）：
 *   1. 编译期版本宏核验：CEC_LIB_VERSION_MAJOR/MINOR 与 7.1 断言一致；
 *   2. 运行时版本一致性：_LIBCEC_VERSION_CURRENT 与 clientVersion 匹配；
 *   3. 无 CEC 硬件环境下 initialise/destroy 生命周期正常（上游在无设备时
 *      仅返回空适配器列表，不得崩溃；OHOS 上同样成立）。
 *   4. libcec_detect_adapters 在无适配器设备上优雅返回（≥0，不崩溃）。
 */
#include <stdio.h>
#include <string.h>

#include <libcec/cecc.h>
#include <libcec/version.h>

int main(void)
{
    int8_t found = -1;
    libcec_configuration config;
    libcec_connection_t conn = NULL;

    /* 1. 编译期版本宏断言 */
    printf("CEC_LIB_VERSION_MAJOR=%d MINOR=%d\n", CEC_LIB_VERSION_MAJOR, CEC_LIB_VERSION_MINOR);
    if (CEC_LIB_VERSION_MAJOR != 7 || CEC_LIB_VERSION_MINOR != 1)
    {
        fprintf(stderr, "FAIL: version macros mismatch (expected 7.1.x)\n");
        return 1;
    }

    /* 2+3. 初始化后读取配置，验证 clientVersion 与 _LIBCEC_VERSION_CURRENT 一致 */
    memset(&config, 0, sizeof(config));
    libcec_clear_configuration(&config);
    config.clientVersion = _LIBCEC_VERSION_CURRENT;
    strncpy(config.strDeviceName, "ohos-platform", LIBCEC_OSD_NAME_SIZE - 1);
    config.strDeviceName[LIBCEC_OSD_NAME_SIZE - 1] = '\0';

    conn = libcec_initialise(&config);
    if (!conn)
    {
        fprintf(stderr, "FAIL: libcec_initialise on OHOS returned NULL\n");
        return 1;
    }

    if (config.clientVersion != _LIBCEC_VERSION_CURRENT)
    {
        fprintf(stderr, "FAIL: clientVersion does not round-trip\n");
        libcec_destroy(conn);
        return 1;
    }

    /* 4. 无 CEC 硬件: 适配器探测必须优雅返回（0 表示无适配器，不得崩溃） */
    {
        cec_adapter_descriptor list[8];
        memset(list, 0, sizeof(list));
        found = libcec_detect_adapters(conn, list, 8, NULL, 1);
    }
    printf("libcec_detect_adapters rc=%d (0 = no adapter on OHOS test host)\n", (int)found);
    if (found < 0)
    {
        fprintf(stderr, "FAIL: detect_adapters crashed/failed on OHOS (rc=%d)\n", (int)found);
        libcec_destroy(conn);
        return 1;
    }

    libcec_destroy(conn);
    printf("PASS: libcec 7.1.1 HarmonyOS-specific test\n");
    return 0;
}