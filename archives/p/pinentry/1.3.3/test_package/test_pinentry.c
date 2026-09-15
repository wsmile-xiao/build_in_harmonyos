/*
 * test_pinentry.c — Test pinentry binaries (L1 consumer test)
 *
 * This test calls pinentry-curses and pinentry-tty with --version and
 * **asserts the reported version string is 1.3.3** — not merely that the
 * process exited 0. Capturing the output is what makes a version regression
 * (e.g. accidentally packaging the 1.3.2 binary) actually fail this test.
 *
 * Expected output shape (实测):
 *   pinentry-curses (pinentry) 1.3.3
 *   ...
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "1.3.3"

/* Run `<binary> --version`, capture stdout+stderr, and require that the
 * output contains EXPECTED_VERSION. Returns 0 on success, non-zero on failure. */
static int check_version(const char *binary) {
    char cmd[512];
    char buf[4096];
    size_t used = 0;
    int found = 0;
    FILE *fp;
    int status;

    /* 2>&1: pinentry 把版本信息输出到 stdout，但一并捕获以防未来变化 */
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", binary);

    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: %s: popen failed\n", binary);
        return 1;
    }

    buf[0] = '\0';
    while (used + 1 < sizeof(buf)) {
        size_t n = fread(buf + used, 1, sizeof(buf) - 1 - used, fp);
        if (n == 0) {
            break;
        }
        used += n;
    }
    buf[used] = '\0';

    status = pclose(fp);
    if (status != 0) {
        fprintf(stderr, "FAIL: %s --version exited non-zero (%d)\n",
                binary, status);
        return 1;
    }

    /* 断言：输出中必须出现期望版本号 */
    if (strstr(buf, EXPECTED_VERSION) != NULL) {
        found = 1;
    }

    /* 同时确认是「本二进制」的版本行，而非恰好匹配到别处的字符串 */
    if (found) {
        char needle[128];
        snprintf(needle, sizeof(needle), "%s (pinentry) %s",
                 binary, EXPECTED_VERSION);
        if (strstr(buf, needle) == NULL) {
            fprintf(stderr,
                    "FAIL: %s: 输出了版本号 %s 但缺少期望的标识行 \"%s\"\n"
                    "------ 实际输出 ------\n%s\n----------------------\n",
                    binary, EXPECTED_VERSION, needle, buf);
            return 1;
        }
    } else {
        fprintf(stderr,
                "FAIL: %s --version 输出中未找到版本号 %s\n"
                "------ 实际输出 ------\n%s\n----------------------\n",
                binary, EXPECTED_VERSION, buf);
        return 1;
    }

    printf("PASS: %s --version reports %s\n", binary, EXPECTED_VERSION);
    return 0;
}

int main(void) {
    int failures = 0;

    failures += check_version("pinentry-curses");
    failures += check_version("pinentry-tty");

    if (failures != 0) {
        fprintf(stderr, "FAIL: %d 项版本断言未通过\n", failures);
        return 1;
    }

    printf("PASS: 两个前端的版本号均断言为 %s\n", EXPECTED_VERSION);
    return 0;
}
