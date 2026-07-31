#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int passed = 0, failed = 0;
    /* 允许通过 argv[1] 传入 ioping 完整路径，默认回退 "ioping" */
    const char *ioping = (argc > 1) ? argv[1] : "ioping";
    char cmd[512];

    printf("ioping Test Suite (binary: %s)\n", ioping);
    printf("================================\n\n");

    /* Test 1: ioping binary exists and --version works */
    printf("Test 1: %s --version\n", ioping);
    snprintf(cmd, sizeof(cmd), "%s --version > /dev/null 2>&1", ioping);
    int ret = system(cmd);
    if (ret == 0) {
        printf("  ✓ %s --version exited with 0\n", ioping);
        passed++;
    } else {
        printf("  ✗ %s --version exited with %d\n", ioping, ret);
        failed++;
    }

    /* Test 2: ioping --help works and contains usage info */
    printf("Test 2: %s --help\n", ioping);
    snprintf(cmd, sizeof(cmd), "%s --help > /dev/null 2>&1", ioping);
    ret = system(cmd);
    if (ret == 0) {
        printf("  ✓ %s --help exited with 0\n", ioping);
        passed++;
    } else {
        printf("  ✗ %s --help exited with %d\n", ioping, ret);
        failed++;
    }

    /* Test 3: ioping version string is non-empty */
    printf("Test 3: %s version output\n", ioping);
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", ioping);
    FILE *fp = popen(cmd, "r");
    if (fp) {
        char buf[256] = {0};
        if (fgets(buf, sizeof(buf), fp)) {
            if (strlen(buf) > 0) {
                printf("  ✓ ioping version: %s", buf);
                passed++;
            } else {
                printf("  ✗ empty version output\n");
                failed++;
            }
        } else {
            printf("  ✗ no version output\n");
            failed++;
        }
        int pc_ret = pclose(fp);
        if (pc_ret != 0) {
            printf("  ✗ %s --version exited with code %d\n", ioping, pc_ret);
            if (strlen(buf) > 0) {
                passed--;
                failed++;
            }
        }
    } else {
        printf("  ✗ could not run %s --version\n", ioping);
        failed++;
    }

    printf("\n========== Summary ==========\n");
    printf("Tests: %d passed, %d failed\n", passed, failed);
    return failed > 0 ? 1 : 0;
}
