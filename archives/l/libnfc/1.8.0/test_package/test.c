/**
 * test_libnfc — 消费者视角验证（Conan L1 官方测试）
 *
 * 真实调用 libnfc 公开 API：
 *   - nfc_version()  返回编译期 PACKAGE_VERSION
 *   - nfc_init()     初始化 NFC 上下文
 *   - nfc_exit()     释放 NFC 上下文
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <nfc/nfc.h>

int main(void)
{
    nfc_context *context = NULL;
    const char *version;

    /* 验证版本 API（编译期宏与运行时一致） */
    version = nfc_version();
    if (version == NULL) {
        fprintf(stderr, "FAIL: nfc_version() returned NULL\n");
        return 1;
    }
    if (strcmp(version, "1.8.0") != 0) {
        fprintf(stderr, "FAIL: nfc_version() = \"%s\" (expected \"1.8.0\")\n", version);
        return 1;
    }

    /* 验证上下文生命周期 API */
    nfc_init(&context);
    if (context == NULL) {
        fprintf(stderr, "FAIL: nfc_init() left context NULL\n");
        return 1;
    }
    nfc_exit(context);

    printf("test libnfc 1.8.0: OK (nfc_version=%s)\n", version);
    return 0;
}
