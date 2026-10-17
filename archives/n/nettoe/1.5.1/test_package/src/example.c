// R34: 实质调用 nettoe 二进制 — --version 输出验证
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    // popen 捕获 `nettoe --version` 输出并验证包含 "netToe" 与版本号，
    // 证明二进制可执行且功能完整（非空壳测试）。
    // argv[1] 传 nettoe 二进制完整路径（不依赖 PATH 查找）。
    const char *nettoe = (argc > 1) ? argv[1] : "nettoe";
    char cmd[512];
    int cmd_len = snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", nettoe);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("nettoe --version: FAILED (command truncated)\n");
        return 1;
    }
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("nettoe --version: FAILED (popen failed)\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);
    if (n > 0 && strstr(buf, "netToe") != NULL && strstr(buf, "1.5.1") != NULL) {
        printf("nettoe --version: OK (output: %s", buf);
        if (buf[n - 1] != '\n') printf("\n");
        return 0;
    }
    printf("nettoe --version: FAILED (unexpected output: %s)\n", buf);
    return 1;
}