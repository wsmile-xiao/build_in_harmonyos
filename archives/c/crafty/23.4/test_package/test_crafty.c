/* test_crafty.c — crafty 消费者测试
 * 编译并运行，校验 crafty 二进制：
 *   1. 二进制存在且可执行
 *   2. --version 或启动 banner 含 "Crafty v23.4"
 * 通过 self.run() 实跑测试程序，满足 R34 + L0 no_test_sources 门禁。
 * 退出码：0=通过，非 0=失败
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <crafty_binary>\n", argv[0]);
        return 2;
    }
    const char *crafty = argv[1];
    if (access(crafty, X_OK) != 0) {
        fprintf(stderr, "FAIL: crafty binary not found or not executable: %s\n", crafty);
        return 3;
    }
    /* pipe "quit" to crafty, capture stdout banner */
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "printf \"quit\\n\" | \"%s\" 2>&1", crafty);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run crafty\n");
        return 4;
    }
    char buf[4096];
    int found_banner = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "Crafty v23.4")) {
            found_banner = 1;
            break;
        }
    }
    pclose(fp);
    if (!found_banner) {
        fprintf(stderr, "FAIL: crafty did not print expected version banner\n");
        return 5;
    }
    printf("crafty: binary OK, version banner present\n");
    return 0;
}
