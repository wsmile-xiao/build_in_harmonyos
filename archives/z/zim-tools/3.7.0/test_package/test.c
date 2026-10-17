/* test_package/test.c — zim-tools 3.7.0
 *
 * R34: Test must exercise the package's binary, not just print a string.
 * zim-tools is a command-line tool (not a linkable library), so we invoke
 * zimdump --help via popen() and verify the process runs successfully and
 * its output identifies the tool.
 *
 * The zimdump binary path is provided via the ZIMDUMP_PATH environment
 * variable (set by CTest from conanfile.py test()'s ZIMDUMP_BIN variable).
 * Falls back to "zimdump" in PATH.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_NAME "zimdump"

int main(void) {
    FILE *fp;
    char buf[512];
    int found = 0;
    char cmd[512];

    /* Get zimdump binary path from environment, or fall back to PATH search */
    const char *zimdump_path = getenv("ZIMDUMP_PATH");
    if (zimdump_path == NULL || zimdump_path[0] == '\0') {
        zimdump_path = "zimdump";
    }

    /* Run zimdump --help and capture output */
    snprintf(cmd, sizeof(cmd), "%s --help 2>&1", zimdump_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    /* Read all output to avoid SIGPIPE when pclose closes the pipe
     * while zimdump is still writing (OHOS pipe buffer timing issue) */
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED_NAME) != NULL) {
            found = 1;
        }
    }
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: zimdump exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: zimdump --help output does not contain '%s'\n",
                EXPECTED_NAME);
        return 1;
    }

    printf("test zim-tools 3.7.0: OK (zimdump runs and identifies itself)\n");
    return 0;
}
