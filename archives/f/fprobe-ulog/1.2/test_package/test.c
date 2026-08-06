/* test.c — L1 test for fprobe-ulog
 * R34: Must actually exercise the tested package.
 * This test locates the fprobe-ulog binary and runs it with -h,
 * verifying the output contains expected version info.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char cmd[256];
    FILE *fp;
    char buf[512];
    int found_version = 0;
    int found_usage = 0;

    /* Run fprobe-ulog -h; it exits with non-zero (wrong params)
     * but still prints version + usage to stderr/stdout */
    snprintf(cmd, sizeof(cmd), "fprobe-ulog -h 2>&1");
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "ERROR: cannot run fprobe-ulog\n");
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "fprobe-ulog") && strstr(buf, "1.2"))
            found_version = 1;
        if (strstr(buf, "Usage") || strstr(buf, "NetFlow"))
            found_usage = 1;
    }
    pclose(fp);

    if (!found_version) {
        fprintf(stderr, "FAIL: version string not found\n");
        return 1;
    }
    if (!found_usage) {
        fprintf(stderr, "FAIL: usage/NetFlow not found\n");
        return 1;
    }

    printf("test fprobe-ulog 1.2: OK (version + usage verified)\n");
    return 0;
}
