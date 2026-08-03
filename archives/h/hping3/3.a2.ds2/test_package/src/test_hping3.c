// test_hping3.c — 消费者视角验证 hping3 二进制可执行
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int passed = 0, failed = 0;
    const char *hping3 = (argc > 1) ? argv[1] : "hping3";
    char cmd[512];

    printf("hping3 Test Suite (binary: %s)\n", hping3);
    printf("================================\n\n");

    /* Test 1: hping3 --version 输出版本号 */
    printf("Test 1: %s --version\n", hping3);
    snprintf(cmd, sizeof(cmd), "%s --version > /dev/null 2>&1", hping3);
    int ret = system(cmd);
    if (ret == 0) {
        printf("  ✓ %s --version exited with 0\n", hping3);
        passed++;
    } else {
        printf("  ✗ %s --version exited with %d\n", hping3, ret);
        failed++;
    }

    /* Test 2: hping3 --help 输出帮助信息 */
    printf("Test 2: %s --help\n", hping3);
    snprintf(cmd, sizeof(cmd), "%s --help > /dev/null 2>&1", hping3);
    ret = system(cmd);
    if (ret == 0) {
        printf("  ✓ %s --help exited with 0\n", hping3);
        passed++;
    } else {
        printf("  ✗ %s --help exited with %d\n", hping3, ret);
        failed++;
    }

    /* Test 3: hping3 版本字符串非空 */
    printf("Test 3: %s version output\n", hping3);
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", hping3);
    FILE *fp = popen(cmd, "r");
    if (fp) {
        char buf[256] = {0};
        int has_output = 0;
        if (fgets(buf, sizeof(buf), fp)) {
            if (strlen(buf) > 0) {
                has_output = 1;
                printf("  ✓ version output: %s", buf);
            }
        }
        int pc_ret = pclose(fp);
        if (has_output && pc_ret == 0) {
            passed++;
        } else {
            printf("  ✗ no valid version output (exit=%d)\n", pc_ret);
            failed++;
        }
    } else {
        printf("  ✗ could not run %s --version\n", hping3);
        failed++;
    }

    printf("\n========== Summary ==========\n");
    printf("Tests: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
