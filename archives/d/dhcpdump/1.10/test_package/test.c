/* test_package/test.c - dhcpdump 1.10
 *
 * dhcpdump is a command-line tool, so this test invokes the packaged binary
 * and verifies its version output instead of linking a library target.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "1.10"

int main(void)
{
    const char *dhcpdump_path = getenv("DHCPDUMP_PATH");
    char cmd[512];
    char buf[512];
    int found = 0;
    FILE *fp;
    int rc;

    if (dhcpdump_path == NULL || dhcpdump_path[0] == '\0') {
        dhcpdump_path = "dhcpdump";
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", dhcpdump_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED_VERSION) != NULL && strstr(buf, "dhcpdump") != NULL) {
            found = 1;
        }
    }

    rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: dhcpdump exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: dhcpdump --version output did not identify dhcpdump %s\n", EXPECTED_VERSION);
        return 1;
    }

    printf("test dhcpdump 1.10: OK\n");
    return 0;
}
