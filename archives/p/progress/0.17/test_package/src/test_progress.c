// R34: 实质调用 progress 二进制 — --version 输出验证
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    // popen 捕获 progress --version 输出并检查（验证二进制可执行且输出
    // 版本信息，非空壳——参考 abduco test 模式）。argv[1] 传 progress
    // 二进制完整路径（usr/bin/progress——make install PREFIX=/usr）
    const char *pr = (argc > 1) ? argv[1] : "progress";
    char cmd[512];
    int cmd_len = snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", pr);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("progress --version: FAILED (command truncated)\n");
        return 1;
    }
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("progress --version: FAILED (popen failed)\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    int rc = pclose(fp);
    /* 同时检查输出非空与命令正常退出（pclose 返回值——二进制缺失/崩溃/
     * 异常退出的错误消息会被误判为有效输出——需退出码 0 才判定通过） */
    if (n > 0 && rc == 0) {
        printf("progress --version: OK (output %zu bytes)\n", n);
        return 0;
    }
    if (n > 0) {
        printf("progress --version: FAILED (exit status %d——命令执行异常)\n", rc);
        return 1;
    }
    printf("progress --version: FAILED (no output)\n");
    return 1;
}
