/* test_package/test.c — iproute2 6.11.0
 *
 * R34: The test must exercise the package's binary, not just print a string.
 * iproute2 ships command-line tools (not a library), so we invoke `ip -V`
 * via popen() and verify the output contains the expected version string.
 *
 * The ip binary path is provided via the IP_PATH environment variable
 * (set by conanfile.py test() method). Falls back to "ip" in PATH.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "iproute2-6.11.0"

int main(void) {
    FILE *fp;
    char buf[512];
    int found = 0;
    char cmd[512];

    const char *ip_path = getenv("IP_PATH");
    if (ip_path == NULL || ip_path[0] == '\0') {
        ip_path = "ip";
    }

    /* `ip -V` prints: "ip utility, iproute2-6.11.0" */
    snprintf(cmd, sizeof(cmd), "%s -V 2>&1", ip_path);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot run '%s'\n", cmd);
        return 1;
    }

    /* Drain all output to avoid SIGPIPE on OHOS pipe buffer timing. */
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, EXPECTED_VERSION) != NULL) {
            found = 1;
        }
    }
    int rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "ERROR: ip exited with status %d\n", rc);
        return 1;
    }

    if (!found) {
        fprintf(stderr, "ERROR: 'ip -V' output does not contain '%s'\n", EXPECTED_VERSION);
        return 1;
    }

    printf("test iproute2 6.11.0: OK (version verified)\n");
    return 0;
}
