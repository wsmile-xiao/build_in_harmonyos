#include <stdio.h>
#include <stdlib.h>

/* Consumer test for the powerstat CLI tool (application package).
 * Verifies the publicly installed binary is runnable and reports its
 * version/help output — a real invocation with observable result. */
int main(void) {
    const char *cmd = "powerstat -h 2>&1 | grep -q 'version 0.04.06'";
    int rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "FAIL: powerstat CLI not runnable (rc=%d)\n", rc);
        return 1;
    }
    return 0;
}