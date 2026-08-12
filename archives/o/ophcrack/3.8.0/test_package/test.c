/* test_package/test.c - ophcrack 3.8.0
 *
 * ophcrack is a command-line tool, so this test invokes the packaged binary
 * and verifies its version output instead of linking a library target.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED "ophcrack 3.8.0"

int main(void)
{
    const char *ophcrack_path = getenv("OPHCRACK_PATH");
    char cmd[512];
    char buf[512];
    int found = 0;
    FILE *fp;
    int rc;

    if (ophcrack_path == NULL || ophcrack_path[0] == '\0') {
        ophcrack_path = "ophcrack";
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" -h 2>&1", ophcrack_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED) != NULL) {
            found = 1;
        }
    }

    rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: ophcrack exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: ophcrack -h output did not identify %s\n", EXPECTED);
        return 1;
    }

    printf("test ophcrack 3.8.0: OK\n");
    return 0;
}
