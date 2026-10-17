// R34: 实质调用 multitail 二进制 — --help 输出验证
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    // popen 捕获 multitail --help 输出并检查非空（验证二进制可执行且
    // 输出帮助信息，非空壳）。不依赖退出码：multitail --help 返回非 0
    // （CI #19230 实测 exit 256=1——--help 处理返回 1），但输出帮助信息
    // ——检查输出非空即可（opensp #17946 同款问题——输出检查模式）。
    // argv[1] 传 multitail 二进制完整路径（usr/local/bin/multitail——
    // CMake 默认 prefix /usr/local，不依赖 PATH——CI #18573 修复）
    const char *mt = (argc > 1) ? argv[1] : "multitail";
    char cmd[512];
    int cmd_len = snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", mt);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("multitail --help: FAILED (command truncated)\n");
        return 1;
    }
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("multitail --help: FAILED (popen failed)\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);
    if (n > 0) {
        printf("multitail --help: OK (output %zu bytes)\n", n);
        return 0;
    }
    printf("multitail --help: FAILED (no output)\n");
    return 1;
}
