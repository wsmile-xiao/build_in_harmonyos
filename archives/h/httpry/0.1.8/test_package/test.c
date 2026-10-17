/* test_package/test.c - httpry 0.1.8
 *
 * httpry is a command-line tool, so this test invokes the packaged binary
 * and verifies its version output instead of linking a library target.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "0.1.8"

int main(void)
{
    const char *httpry_path = getenv("HTTPRY_PATH");
    char cmd[512];
    char buf[512];
    int found = 0;
    FILE *fp;
    int rc;

    if (httpry_path == NULL || httpry_path[0] == '\0') {
        httpry_path = "httpry";
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" -h 2>&1", httpry_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED_VERSION) != NULL && strstr(buf, "httpry") != NULL) {
            found = 1;
        }
    }

    rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: httpry exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: httpry -h output did not contain httpry %s\n", EXPECTED_VERSION);
        return 1;
    }

    printf("test httpry 0.1.8: OK\n");
    return 0;
}
