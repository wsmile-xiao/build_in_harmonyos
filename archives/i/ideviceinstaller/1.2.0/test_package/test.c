// test_ideviceinstaller.c — ideviceinstaller L1 test binary.
//
// R34: test_package must make substantive use of the tested package.
// ideviceinstaller is a CLI tool; verification captures `--version` and
// `--help` output and checks exit code + non-empty output (sandbox has no
// iOS device to manage, so runnability is verified via CLI options).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_output(const char *path, const char *arg) {
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s %s 2>/dev/null", path, arg);

    // 断言: 命令可执行（退出码为 0）
    int ret = system(cmd);
    if (ret != 0) {
        printf("ideviceinstaller %s: FAILED (exit %d)\n", arg, ret);
        return 1;
    }
    printf("ideviceinstaller %s: exit code OK\n", arg);

    // 断言: 输出非空
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        printf("ideviceinstaller %s: popen FAILED\n", arg);
        return 1;
    }
    char buf[256] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        printf("ideviceinstaller %s: no output\n", arg);
        pclose(fp);
        return 1;
    }
    pclose(fp);
    printf("ideviceinstaller %s: output: %s", arg, buf);
    return 0;
}

int main(int argc, char *argv[]) {
    const char *bin_path = "ideviceinstaller";
    if (argc > 1) {
        bin_path = argv[1];
    }

    if (check_output(bin_path, "--version") != 0)
        return 1;
    if (check_output(bin_path, "--help") != 0)
        return 1;

    printf("test_ideviceinstaller: ALL PASS\n");
    return 0;
}
