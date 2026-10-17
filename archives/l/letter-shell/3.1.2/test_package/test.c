/* test_package 消费者验证 — letter-shell 3.1.2
 *
 * 消费者用例：模拟业务上层组件，仅通过库已安装/导出的公开头文件 (shell.h)
 * 与公开 API 使用 letter-shell：
 *   1) shellInit 初始化 shell 对象
 *   2) SHELL_EXPORT_CMD 导出用户命令 add（业务上层自定义命令）
 *   3) shellRun 直接执行 "add 3 4" 并校验输出包含正确结果 "7"
 * 任一断言失败非零退出。
 */
#include "shell.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char outBuf[4096];
static unsigned int outLen = 0;

/* shell 输出回调：捕获库输出到本地缓冲区用于断言 */
static signed short myWrite(char *data, unsigned short len)
{
    if (outLen + len < sizeof(outBuf)) {
        memcpy(outBuf + outLen, data, len);
        outLen += len;
    }
    return (signed short)len;
}

/* 业务命令：add a b —— 输出两整数之和（main 型命令，argc/argv 参数） */
static int cmdAdd(int argc, char *argv[])
{
    if (argc < 3) {
        shellPrint(shellGetCurrent(), "usage: add a b\r\n");
        return 0;
    }
    shellPrint(shellGetCurrent(), "%d\r\n", atoi(argv[1]) + atoi(argv[2]));
    return 0;
}
SHELL_EXPORT_CMD(SHELL_CMD_PERMISSION(0)|SHELL_CMD_TYPE(SHELL_TYPE_CMD_MAIN)|SHELL_CMD_PARAM_NUM(2),
                 add, cmdAdd, add two ints);

int main(void)
{
    Shell shell;
    char buf[512];
    int rc;

    memset(outBuf, 0, sizeof(outBuf));
    memset(&shell, 0, sizeof(shell));
    shell.write = myWrite;
    shellInit(&shell, buf, sizeof(buf));
    if (shell.commandList.count == 0) {
        printf("FAIL: command list empty after shellInit\n");
        return 1;
    }

    outLen = 0;
    rc = shellRun(&shell, "add 3 4");
    if (rc != 0) {
        printf("FAIL: shellRun rc=%d\n", rc);
        return 2;
    }
    if (strstr(outBuf, "7") == NULL) {
        printf("FAIL: output missing result 7, got=[%s]\n", outBuf);
        return 3;
    }

    outLen = 0;
    rc = shellRun(&shell, "add 10 32");
    if (rc != 0 || strstr(outBuf, "42") == NULL) {
        printf("FAIL: second add run, rc=%d out=[%s]\n", rc, outBuf);
        return 4;
    }

    printf("PASS: consumer add command executed, outputs verified (7, 42)\n");
    return 0;
}