#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Smoke test for epic5 (R34): invoke the installed epic5 binary with
 * -v and verify its version output contains "EPIC5".  The binary path
 * is taken from the EPIC5_BIN environment variable (set by the Conan
 * test_package conanfile.py); if unset, fall back to "epic5" on PATH.
 */
int main(void) {
    const char *bin = getenv("EPIC5_BIN");
    if (!bin || !*bin)
        bin = "epic5";

    char cmd[256];
    snprintf(cmd, sizeof(cmd), "%s -v 2>&1", bin);

    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "epic5: cannot launch binary (%s)\n", bin);
        return 1;
    }

    int found = 0;
    char buf[512];
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, "EPIC5") != NULL)
            found = 1;
    }

    int rc = pclose(fp);
    if (rc != 0 || !found) {
        fprintf(stderr,
                "epic5: version check failed (rc=%d, found=%d)\n",
                rc, found);
        return 1;
    }
    return 0;
}
