#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int passed = 0, failed = 0;
    /* 允许通过 argv[1] 传入 meinproc 二进制完整路径，默认回退 "meinproc" */
    const char *meinproc = (argc > 1) ? argv[1] : "meinproc";
    char cmd[512];
    char buf[4096];
    size_t n;

    printf("kdoctools Test Suite (binary: %s)\n", meinproc);
    printf("================================\n\n");

    /* Test 1: meinproc binary --help outputs usage info.
     * 不依赖退出码（上游可能非零），用 popen 捕获输出并检查关键字。 */
    printf("Test 1: %s --help (output check)\n", meinproc);
    int cmd_len = snprintf(cmd, sizeof(cmd), "%s --help 2>&1", meinproc);
    if (cmd_len < 0 || (size_t)cmd_len >= sizeof(cmd)) {
        printf("  ✗ command line too long (need %d, have %zu)\n", cmd_len, sizeof(cmd));
        failed++;
    } else {
        FILE *fp = popen(cmd, "r");
        if (fp == NULL) {
            printf("  ✗ popen failed\n");
            failed++;
        } else {
            n = fread(buf, 1, sizeof(buf) - 1, fp);
            buf[n] = '\0';
            pclose(fp);
            /* AI review P2：删除 "meinproc" 关键字（命令未找到/加载失败
             * 的错误消息含 "meinproc"——假阳性误报 PASS——与 fizmo/drill/
             * opensp P2 教训相同）——仅 "Usage"/"usage" + 输出非空检查 */
            if (n > 0 &&
                (strstr(buf, "Usage") != NULL || strstr(buf, "usage") != NULL)) {
                printf("  ✓ %s --help printed usage info\n", meinproc);
                passed++;
            } else {
                printf("  ✗ %s --help output missing usage info\n", meinproc);
                failed++;
            }
        }
    }

    printf("\n================================\n");
    printf("Result: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
