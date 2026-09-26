/*
 * test.c — libcec 7.1.1 消费者用例（L1 test_package）
 *
 * 模拟业务上层组件：仅经 libcec 安装导出的公开头文件 <libcec/cecc.h>、
 * 公开 C API（libcec_clear_configuration / libcec_initialise /
 * libcec_get_lib_info / libcec_destroy）编译、链接、调用并运行，
 * 验证第三方使用者能在 HarmonyOS 上正常初始化和销毁 libCEC 实例。
 */
#include <stdio.h>
#include <string.h>

#include <libcec/cecc.h>
#include <libcec/version.h>

int main(void)
{
    const char *info = NULL;
    libcec_configuration config;
    libcec_connection_t conn = NULL;

    memset(&config, 0, sizeof(config));
    libcec_clear_configuration(&config);
    config.clientVersion = _LIBCEC_VERSION_CURRENT;
    strncpy(config.strDeviceName, "ohos-consumer", LIBCEC_OSD_NAME_SIZE - 1);
    config.strDeviceName[LIBCEC_OSD_NAME_SIZE - 1] = '\0';
    config.bActivateSource = 0;

    conn = libcec_initialise(&config);
    if (!conn)
    {
        fprintf(stderr, "FAIL: libcec_initialise returned NULL\n");
        return 1;
    }

    info = libcec_get_lib_info(conn);
    if (!info || !*info)
    {
        fprintf(stderr, "FAIL: libcec_get_lib_info returned empty string\n");
        libcec_destroy(conn);
        return 1;
    }
    printf("libcec lib info: %s\n", info);

    libcec_destroy(conn);
    printf("PASS: libcec 7.1.1 consumer test (initialise/get_lib_info/destroy)\n");
    return 0;
}