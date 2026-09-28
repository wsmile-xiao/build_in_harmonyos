/*
 * HarmonyOS 消费者用例测试（新增，R51 补全测试用例）。
 *
 * wmmp 包的交付物是可执行文件 WMmp（无导出头文件/库），消费者集成形态
 * 即为执行该二进制。本用例覆盖其真实命令行入口：
 *   - "WMmp -v"：打印 "WMmp version ..." 并 exit(0)
 *   - "WMmp -h"：打印 "Usage : ..." 并 exit(0)
 * 两个入口都在 parse_arguments() 内退出，发生在打开 X 显示之前，
 * 因而无 X server 环境下结果确定；同时验证 OHOS ELF 能完成动态链接
 * （libX11/libXext/libXpm 全部解析成功）并真正运行。
 *
 * 被测二进制路径经 WMMP_BIN 环境变量传入（test_package/conanfile.py），
 * 未设置时回退到 PATH 中的 WMmp。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef WMMP_BIN_ENV
#define WMMP_BIN_ENV "WMMP_BIN"
#endif

static int run_case(const char *args, const char *expect)
{
    const char *bin = getenv(WMMP_BIN_ENV);
    if (!bin || bin[0] == '\0')
        bin = "WMmp";
    char cmd[2048];
    snprintf(cmd, sizeof(cmd), "\"%s\" %s 2>&1", bin, args);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        printf("FAIL: popen(%s) failed\n", cmd);
        return 1;
    }
    char out[4096] = {0};
    size_t n = fread(out, 1, sizeof(out) - 1, fp);
    int status = pclose(fp);
    if (status != 0) {
        printf("FAIL: %s exited with status %d\noutput: %s\n", cmd, status, out);
        return 1;
    }
    if (n == 0 || strstr(out, expect) == NULL) {
        printf("FAIL: %s output does not contain \"%s\"\noutput: %s\n",
               cmd, expect, out);
        return 1;
    }
    printf("PASS: %s\noutput: %s", cmd, out);
    return 0;
}

int main(void)
{
    int failures = 0;
    failures += run_case("-v", "version");
    failures += run_case("-h", "Usage");
    if (failures != 0) {
        printf("wmmp consumer tests: %d case(s) FAILED\n", failures);
        return 1;
    }
    printf("wmmp consumer tests: all cases PASSED\n");
    return 0;
}
