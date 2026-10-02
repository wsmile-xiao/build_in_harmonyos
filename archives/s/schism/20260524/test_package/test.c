/*
 * schism 鸿蒙特有测试（消费者完整用例，非纯断言）
 *
 * 消费路径：真实执行包内 schismtracker 可执行文件（SDL2 音轨软件的
 * headless 冒烟验证）：
 *   1. 运行 --version 校验产物可执行性与版本自报告
 *   2. 运行 --help 校验 CLI 契约完整（退出码 0）
 *   （schismtracker 为交互式 TUI 程序，无显示环境时主动退出，
 *     以 version/help 为消费者可验证契约）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* SCHISM_BIN 由 test_package conanfile 注入 */
#include <stdlib.h>

static int run_check(const char *bin, const char *args, const char *expect) {
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s %s 2>&1", bin, args);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: popen %s\n", cmd);
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    int rc = pclose(fp);
    if (expect && !strstr(buf, expect)) {
        fprintf(stderr, "FAIL: output missing '%s'\n--- got ---\n%s\n", expect, buf);
        return 1;
    }
    if (rc != 0) {
        fprintf(stderr, "FAIL: exit code %d\n--- output ---\n%s\n", rc, buf);
        return 1;
    }
    printf("PASS: %s %s\n", bin, args);
    return 0;
}

int main(void) {
    const char *bin = getenv("SCHISM_BIN");
    if (!bin || !*bin) {
        fprintf(stderr, "FAIL: SCHISM_BIN not set\n");
        return 2;
    }

    /* 1. 版本自报告（产物可执行 + 版本契约） */
    if (run_check(bin, "--version", "Schism Tracker") != 0)
        return 1;

    /* 2. CLI 契约完整 */
    if (run_check(bin, "--help", "Usage") != 0)
        return 1;

    printf("RESULT: schism 20260524 consumer test OK (version+help)\n");
    return 0;
}
