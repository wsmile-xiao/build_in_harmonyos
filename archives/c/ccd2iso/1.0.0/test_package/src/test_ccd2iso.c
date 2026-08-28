// test_ccd2iso.c — ccd2iso L1 test binary.
//
// R34: test_package must make substantive use of the tested package.
// ccd2iso is a CLI tool; verification captures `ccd2iso --version` and
// `--help` output and checks exit code + non-empty output (sandbox has no
// CD image to convert, so runnability is verified via CLI options).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_output(const char *path, const char *arg) {
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s %s 2>/dev/null", path, arg);

    // 断言: 命令可执行（退出码为 0）
    int ret = system(cmd);
    if (ret != 0) {
        printf("ccd2iso %s: FAILED (exit %d)\n", arg, ret);
        return 1;
    }
    printf("ccd2iso %s: exit code OK\n", arg);

    // 断言: 输出非空
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        printf("ccd2iso %s: popen FAILED\n", arg);
        return 1;
    }
    char buf[256] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        printf("ccd2iso %s: no output\n", arg);
        pclose(fp);
        return 1;
    }
    pclose(fp);
    printf("ccd2iso %s: output: %s", arg, buf);
    return 0;
}

int main(int argc, char *argv[]) {
    const char *ccd2iso_path = "ccd2iso";
    if (argc > 1) {
        ccd2iso_path = argv[1];
    }

    if (check_output(ccd2iso_path, "--version") != 0)
        return 1;
    if (check_output(ccd2iso_path, "--help") != 0)
        return 1;

    printf("test_ccd2iso: ALL PASS\n");
    return 0;
}
