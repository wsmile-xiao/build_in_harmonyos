/* test_nmap.c — L1 reference test for nmap 7.99
 * R34: test substantively depends on the tested package.
 *
 * This is a reference C test. The Conan test_package uses conanfile.py
 * to verify the binary directly (file/strings/readelf).
 * To compile: clang -o test_nmap test.c && NMAP_PATH=/path/to/nmap ./test_nmap
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const char *nmap_bin = getenv("NMAP_PATH");
    if (!nmap_bin) {
        fprintf(stderr, "FAIL: NMAP_PATH environment variable not set\n");
        return 1;
    }

    /* Validate nmap_bin to prevent command injection */
    for (const char *p = nmap_bin; *p; p++) {
        if (*p == ';' || *p == '|' || *p == '&' || *p == '`' ||
            *p == '$' || *p == '(' || *p == ')' || *p == '<' ||
            *p == '>' || *p == '\n' || *p == '\r' ||
            *p == '"' || *p == '\'') {
            fprintf(stderr, "FAIL: NMAP_PATH contains invalid characters\n");
            return 1;
        }
    }

    char cmd[512];
    FILE *fp;
    char buf[256];
    int found_version = 0;
    int found_scan = 0;
    int ret;

    /* Test 1: nmap --version */
    ret = snprintf(cmd, sizeof(cmd), "%s --version 2>&1", nmap_bin);
    if (ret < 0 || (size_t)ret >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command too long\n");
        return 1;
    }
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run nmap --version\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "7.99")) found_version = 1;
    }
    ret = pclose(fp);
    if (ret != 0) {
        fprintf(stderr, "FAIL: nmap --version exited with status %d\n", ret);
        return 1;
    }
    if (!found_version) {
        fprintf(stderr, "FAIL: nmap --version did not output version 7.99\n");
        return 1;
    }
    printf("PASS: nmap --version outputs version 7.99\n");

    /* Test 2: nmap -sL 127.0.0.1 (list scan) */
    ret = snprintf(cmd, sizeof(cmd), "%s -sL 127.0.0.1 2>&1", nmap_bin);
    if (ret < 0 || (size_t)ret >= sizeof(cmd)) {
        fprintf(stderr, "FAIL: command too long\n");
        return 1;
    }
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run nmap -sL\n");
        return 1;
    }
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "127.0.0.1") || strstr(buf, "localhost")) found_scan = 1;
    }
    ret = pclose(fp);
    if (ret != 0) {
        fprintf(stderr, "FAIL: nmap -sL exited with status %d\n", ret);
        return 1;
    }
    if (!found_scan) {
        fprintf(stderr, "FAIL: nmap -sL did not output expected results\n");
        return 1;
    }
    printf("PASS: nmap -sL 127.0.0.1 completed successfully\n");

    printf("All tests passed!\n");
    return 0;
}
