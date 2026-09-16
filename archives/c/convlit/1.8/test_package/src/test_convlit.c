// test_convlit: 实质调用 clit 二进制，验证其可执行并输出版本/使用说明。
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    const char *clit = (argc > 1) ? argv[1] : "clit";
    char cmd[512];
    int cmd_len = snprintf(cmd, sizeof(cmd), "\"%s\" 2>&1", clit);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("convlit run: FAILED (command truncated)\n");
        return 1;
    }
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("convlit run: FAILED (popen failed)\n");
        return 1;
    }
    char buf[4096];
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);
    if (n > 0 && strstr(buf, "ConvertLIT") != NULL) {
        printf("convlit run: OK (output %zu bytes)\n", n);
        return 0;
    }
    printf("convlit run: FAILED (no output)\n");
    return 1;
}
