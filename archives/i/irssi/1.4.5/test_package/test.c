#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test: verify irssi binary is installed and returns version info.
 * R34: this test executes the packaged irssi binary and verifies output.
 * Uses popen() to capture irssi --version output and checks for
 * expected version string. */
int main(void) {
    char buf[256];
    FILE *fp;
    int found_version = 0;

    fp = popen("irssi --version", "r");
    if (fp == NULL) {
        fprintf(stderr, "FAIL: cannot run irssi --version\n");
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "irssi") != NULL) {
            found_version = 1;
            printf("irssi version output: %s", buf);
        }
    }

    int ret = pclose(fp);
    if (ret != 0) {
        fprintf(stderr, "FAIL: irssi --version exited with %d\n", ret);
        return 1;
    }

    if (!found_version) {
        fprintf(stderr, "FAIL: irssi version string not found in output\n");
        return 1;
    }

    printf("PASS: irssi binary is functional and reports version\n");
    return 0;
}
