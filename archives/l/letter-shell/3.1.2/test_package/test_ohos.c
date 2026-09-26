/* HarmonyOS 专项测试 — letter-shell 3.1.2
 *
 * 目标：验证 letter-shell 在 OHOS (aarch64-linux-ohos, clang) 工具链下的
 * 平台适配正确性。本文件是真正的 HarmonyOS 专项用例：
 *   - 编译目标固定为 OHOS aarch64（由 Conan profile/工具链保证）
 *   - 运行时断言 __aarch64__ 宏（OHOS PC 平台架构）
 *   - 校验 SHELL_VERSION 字符串与预期版本一致
 *   - 真实执行 SHELL_EXPORT_CMD 导出的命令并校验输出
 * 任一断言失败非零退出。
 */
#include "shell.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef SHELL_VERSION
#define SHELL_VERSION "unknown"
#endif

static char outBuf[4096];
static unsigned int outLen = 0;

static signed short myWrite(char *data, unsigned short len)
{
    if (outLen + len < sizeof(outBuf)) {
        memcpy(outBuf + outLen, data, len);
        outLen += len;
    }
    return (signed short)len;
}

static int cmdMul(int argc, char *argv[])
{
    if (argc < 3) {
        shellPrint(shellGetCurrent(), "usage: mul a b\r\n");
        return 0;
    }
    shellPrint(shellGetCurrent(), "%d\r\n", atoi(argv[1]) * atoi(argv[2]));
    return 0;
}
SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0)|SHELL_CMD_TYPE(SHELL_TYPE_CMD_MAIN)|SHELL_CMD_PARAM_NUM(2),
                 mul, cmdMul, multiply two ints);

int main(void)
{
    Shell shell;
    char buf[512];
    int rc;
    int failures = 0;

#if defined(__aarch64__)
    printf("PLATFORM: __aarch64__ detected -- OHOS arm64 识别正确\n");
#else
    printf("PLATFORM: __aarch64__ NOT defined -- 非预期（OHOS PC 应为 aarch64）\n");
    failures++;
#endif

    if (strcmp(SHELL_VERSION, "3.1.2") != 0) {
        printf("FAIL: SHELL_VERSION=%s, expected 3.1.2\n", SHELL_VERSION);
        failures++;
    } else {
        printf("VERSION: SHELL_VERSION=3.1.2 ok\n");
    }

    memset(outBuf, 0, sizeof(outBuf));
    memset(&shell, 0, sizeof(shell));
    shell.write = myWrite;
    shellInit(&shell, buf, sizeof(buf));

    outLen = 0;
    rc = shellRun(&shell, "mul 6 7");
    if (rc != 0) {
        printf("FAIL: shellRun mul rc=%d\n", rc);
        failures++;
    } else if (strstr(outBuf, "42") == NULL) {
        printf("FAIL: mul output missing 42, got=[%s]\n", outBuf);
        failures++;
    } else {
        printf("EXEC: shellRun mul 6 7 -> 42 ok\n");
    }

    if (failures != 0) {
        printf("RESULT: OHOS 专项测试 %d 项失败\n", failures);
        return 1;
    }
    printf("RESULT: OHOS 专项测试全部通过 (platform=aarch64, version=3.1.2, cmd=mul)\n");
    return 0;
}