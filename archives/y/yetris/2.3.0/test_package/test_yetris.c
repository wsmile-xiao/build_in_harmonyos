/* test_yetris.c — yetris 2.3.0 消费者测试（HarmonyOS PC / OHOS aarch64）
 *
 * yetris 是 application（ncurses TUI 游戏），没有可链接的库 API，因此消费者
 * 测试以"二进制使用者"身份运行打包产物并断言可验证行为（AGENTS §9）：
 *   1. 被测 `yetris` 二进制存在且可执行；
 *   2. `yetris --version` 退出码 0，且输出含 "yetris v2.3.0"（版本契约）；
 *   3. `yetris --help` 退出码 0，输出含 usage 提示且列出 `--version` 选项。
 * 退出码：0=通过，非 0=失败（用于 CI L1「真实执行」闸）。
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* 运行 "<binary> <args>"，捕获合并后的 stdout+stderr，回填真实退出码。
 * 返回 0 成功取到输出，-1 表示无法启动子进程。 */
static int run_and_capture(const char *binary, const char *args,
                           char *out, size_t cap, int *exit_code) {
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "TERM=dumb \"%s\" %s 2>&1", binary, args);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        return -1;
    }
    size_t n = 0;
    int ch;
    while ((ch = fgetc(fp)) != EOF && n + 1 < cap) {
        out[n++] = (char)ch;
    }
    out[n] = '\0';
    int st = pclose(fp);
    *exit_code = WIFEXITED(st) ? WEXITSTATUS(st) : -1;
    return 0;
}

static void to_lower(char *s) {
    for (; *s; ++s) {
        *s = (char)tolower((unsigned char)*s);
    }
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <yetris_binary>\n", argv[0]);
        return 2;
    }
    const char *binary = argv[1];

    if (access(binary, X_OK) != 0) {
        fprintf(stderr, "FAIL: yetris binary missing or not executable: %s\n", binary);
        return 3;
    }

    char out[16384];
    int rc = -1;

    /* ── 断言 1：--version 退出 0 且打印 "yetris v2.3.0" ── */
    if (run_and_capture(binary, "--version", out, sizeof(out), &rc) != 0) {
        fprintf(stderr, "FAIL: cannot spawn 'yetris --version'\n");
        return 4;
    }
    if (rc != 0) {
        fprintf(stderr, "FAIL: 'yetris --version' exit=%d\n%s\n", rc, out);
        return 5;
    }
    if (!strstr(out, "yetris v2.3.0")) {
        fprintf(stderr, "FAIL: '--version' output missing 'yetris v2.3.0'\n%s\n", out);
        return 6;
    }

    /* ── 断言 2：--help 退出 0，含 usage 提示与 --version 选项 ── */
    if (run_and_capture(binary, "--help", out, sizeof(out), &rc) != 0) {
        fprintf(stderr, "FAIL: cannot spawn 'yetris --help'\n");
        return 7;
    }
    if (rc != 0) {
        fprintf(stderr, "FAIL: 'yetris --help' exit=%d\n%s\n", rc, out);
        return 8;
    }
    char lower[sizeof(out)];
    strncpy(lower, out, sizeof(lower) - 1);
    lower[sizeof(lower) - 1] = '\0';
    to_lower(lower);
    if (!strstr(lower, "usage")) {
        fprintf(stderr, "FAIL: '--help' output missing usage text\n%s\n", out);
        return 9;
    }
    if (!strstr(out, "--version")) {
        fprintf(stderr, "FAIL: '--help' output does not list the --version option\n%s\n", out);
        return 10;
    }

    printf("yetris consumer test OK: --version=2.3.0, --help usage screen present\n");
    return 0;
}
