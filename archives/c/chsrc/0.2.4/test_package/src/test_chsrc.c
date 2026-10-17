// test_chsrc.c — chsrc L1 test binary.
//
// R34: test_package must make substantive use of the tested package's API.
// For chsrc (command-line tool), verification captures chsrc --version
// output and checks both exit code and version string content.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    const char *chsrc_path = "chsrc";
    if (argc > 1) {
        chsrc_path = argv[1];
    }

    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s --version 2>/dev/null", chsrc_path);

    // 断言 1: chsrc --version 可执行（退出码为 0）
    int ret = system(cmd);
    if (ret != 0) {
        printf("chsrc --version: FAILED (exit %d)\n", ret);
        return 1;
    }
    printf("chsrc --version: exit code OK\n");

    // 断言 2: 版本号输出包含 v0.2.4
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        printf("popen: FAILED\n");
        return 1;
    }
    char buf[256] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        printf("chsrc --version: no output\n");
        pclose(fp);
        return 1;
    }
    pclose(fp);

    if (strstr(buf, "v0.2.4") == NULL) {
        printf("chsrc --version: version check FAILED (got: %s)", buf);
        return 1;
    }
    printf("chsrc --version: version check OK (v0.2.4)\n");
    return 0;
}
