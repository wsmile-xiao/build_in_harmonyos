/* test_package/test.c — rsync 3.3.0
 *
 * R34: Test must exercise the package's binary, not just print a string.
 * rsync is a command-line tool (not a library), so we invoke rsync --version
 * via popen() and verify the output contains the expected version string.
 *
 * The rsync binary path is provided via the RSYNC_PATH environment variable
 * (set by conanfile.py test() method). Falls back to "rsync" in PATH.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "version 3.3.0"

int main(void) {
    FILE *fp;
    char buf[512];
    int found = 0;
    char cmd[512];

    /* Get rsync binary path from environment, or fall back to PATH search */
    const char *rsync_path = getenv("RSYNC_PATH");
    if (rsync_path == NULL || rsync_path[0] == '\0') {
        rsync_path = "rsync";
    }

    /* Run rsync --version and capture output */
    snprintf(cmd, sizeof(cmd), "%s --version 2>&1", rsync_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    /* Read all output to avoid SIGPIPE when pclose closes the pipe
     * while rsync is still writing (OHOS pipe buffer timing issue) */
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED_VERSION) != NULL) {
            found = 1;
        }
    }
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: rsync exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: rsync --version output does not contain '%s'\n", EXPECTED_VERSION);
        return 1;
    }

    printf("test rsync 3.3.0: OK (version verified)\n");
    return 0;
}
