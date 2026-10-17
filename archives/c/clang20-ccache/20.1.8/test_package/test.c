/*
 * test_package / test.c — clang20-ccache 20.1.8
 *
 * R34: test_package 必须真实调用被测包二进制并断言结果，禁止只打印字符串
 * 的空壳测试。clang20-ccache 是 CLI 工具包（无库 API），因此本测试直接
 * 执行打包的 `ccache --version`，断言：
 *   1) 进程退出码为 0；
 *   2) 输出包含 "ccache version 4.14"（期望版本，tarball 官方 tag v4.14）。
 * `ccache` 通过 conan run 环境 (VirtualRunEnv) 的 PATH 定位到包内 bin/。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char line[512];
    int found = 0;

    fp = popen("ccache --version 2>&1", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: popen(ccache --version) failed\n");
        return 1;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        printf("%s", line);
        if (strstr(line, "ccache version 4.14") != NULL) {
            found = 1;
        }
    }
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "FAIL: ccache --version exit code = %d\n", rc);
        return 1;
    }
    if (!found) {
        fprintf(stderr, "FAIL: expected 'ccache version 4.14' not found\n");
        return 1;
    }
    printf("PASS: ccache binary invoked, version 4.14 confirmed\n");
    return 0;
}