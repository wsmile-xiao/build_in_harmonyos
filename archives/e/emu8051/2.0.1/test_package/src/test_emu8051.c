#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int passed = 0, failed = 0;
    /* 允许通过 argv[1] 传入 emu8051 二进制完整路径，默认回退 "emu" */
    const char *emu = (argc > 1) ? argv[1] : "emu";
    char cmd[512];
    char buf[4096];
    size_t n;

    printf("emu8051 Test Suite (binary: %s)\n", emu);
    printf("================================\n\n");

    /* Test 1: emu8051 binary --help outputs usage info.
     * 注意：emu --help 上游退出码为 255（打印帮助后返回非零），
     * 不能依赖退出码，改为检查输出内容（含 "emu8051"/"Help" 关键字）。 */
    printf("Test 1: %s --help (output check)\n", emu);
    snprintf(cmd, sizeof(cmd), "%s --help 2>&1", emu);
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        printf("  ✗ popen failed\n");
        failed++;
    } else {
        n = fread(buf, 1, sizeof(buf) - 1, fp);
        buf[n] = '\0';
        pclose(fp);
        if (strstr(buf, "emu8051") != NULL || strstr(buf, "Help") != NULL) {
            printf("  ✓ %s --help printed usage info\n", emu);
            passed++;
        } else {
            printf("  ✗ %s --help output missing usage info\n", emu);
            failed++;
        }
    }

    printf("\n================================\n");
    printf("Result: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
