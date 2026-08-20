#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* test.c — L1 test for ctags binary
 *
 * Verifies the ctags binary is installed and functional by:
 * 1. Running `ctags --version` and checking exit code + output
 * 2. Running `ctags --list-languages` to verify parser availability
 *
 * Usage: test_ctags <path-to-ctags-binary>
 * The ctags path is passed as argv[1] to avoid PATH dependency.
 */

int main(int argc, char *argv[]) {
    int ret;
    FILE *fp;
    char buf[512];
    int found_version = 0;
    int found_c_language = 0;
    char cmd[512];

    if (argc < 2) {
        fprintf(stderr, "FAIL: usage: test_ctags <path-to-ctags>\n");
        return 1;
    }

    /* Test 1: ctags --version must succeed and contain "Universal Ctags" */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", argv[1]);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot execute ctags --version\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "Universal Ctags") != NULL) {
            found_version = 1;
        }
    }
    ret = pclose(fp);
    if (ret != 0 || !found_version) {
        fprintf(stderr, "FAIL: ctags --version did not return expected output (exit=%d)\n", ret);
        return 1;
    }
    printf("[test] ctags --version: PASS\n");

    /* Test 2: ctags --list-languages must include C parser */
    snprintf(cmd, sizeof(cmd), "\"%s\" --list-languages 2>&1", argv[1]);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot execute ctags --list-languages\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        /* Strip newline and compare */
        buf[strcspn(buf, "\r\n")] = '\0';
        if (strcmp(buf, "C") == 0) {
            found_c_language = 1;
        }
    }
    ret = pclose(fp);
    if (ret != 0 || !found_c_language) {
        fprintf(stderr, "FAIL: ctags --list-languages did not list C (exit=%d)\n", ret);
        return 1;
    }
    printf("[test] ctags --list-languages (C found): PASS\n");

    printf("ctags L1 test: ALL PASS\n");
    return 0;
}
