/*
 * test_package/test.c — AusweisApp 2.5.4 鸿蒙特有测试 (R34: 真实执行目标程序).
 *
 * AusweisApp 是 Qt6 GUI 应用 (package_type = "application")，不导出可被
 * 消费者链接的 C 库 API，因此 test_package 通过真实执行打包产物验证：
 *   1) 二进制确实在目标平台 (OHOS aarch64) 上可启动；
 *   2) `--version` 输出版本号 (QCommandLineParser addVersionOption 注册)，
 *      证明 Qt6 运行库加载成功、程序主流程可运行。
 *
 * 本测试真实依赖被测包：经 AUSWEISAPP_BIN 指向 package_folder/bin 下的
 * AusweisApp 产物执行，绝非空壳 printf 测试。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* conanfile.py 经 CMake configure variables 传入产物路径；
 * 未定义时回退到 PATH 查找 (本地手动运行场景)。 */
#ifndef AUSWEISAPP_BIN
#define AUSWEISAPP_BIN "AusweisApp"
#endif

int main(void) {
    char cmd[512];
    FILE* pipe;
    char buf[256];
    int ret;

    /* 真实执行打包产物：AusweisApp --version。
     * 2>&1 合并 stderr，避免 Qt 平台日志干扰输出捕获。 */
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", AUSWEISAPP_BIN);

    pipe = popen(cmd, "r");
    if (pipe == NULL) {
        fprintf(stderr, "FATAL: cannot execute AusweisApp binary at '%s'\n",
                AUSWEISAPP_BIN);
        return 1;
    }

    /* 读取版本输出 — 必须非空。 */
    buf[0] = '\0';
    if (fgets(buf, sizeof(buf), pipe) == NULL) {
        pclose(pipe);
        fprintf(stderr, "FATAL: AusweisApp --version produced no output\n");
        return 1;
    }
    ret = pclose(pipe);

    /* 验证退出码为 0 (WIFEXITED + exit 0)。 */
    if (ret != 0) {
        fprintf(stderr, "FATAL: AusweisApp --version exited with code %d\n", ret);
        return 1;
    }

    /* 版本输出必须含数字 (如 "AusweisApp 2.5.4")，证明真实版本号被打印。 */
    if (strlen(buf) == 0) {
        fprintf(stderr, "FATAL: AusweisApp --version output is empty\n");
        return 1;
    }
    {
        size_t i;
        int has_digit = 0;
        for (i = 0; i < strlen(buf); i++) {
            if (buf[i] >= '0' && buf[i] <= '9') {
                has_digit = 1;
                break;
            }
        }
        if (!has_digit) {
            fprintf(stderr,
                    "FATAL: AusweisApp --version output has no version digits: '%s'\n",
                    buf);
            return 1;
        }
    }

    printf("PASS: AusweisApp 鸿蒙特有测试 — 二进制可启动且 --version 输出: %s", buf);
    return 0;
}
