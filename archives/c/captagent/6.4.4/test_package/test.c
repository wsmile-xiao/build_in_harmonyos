/*
 * Test driver for captagent (SIP/RTP packet capture agent) on OHOS.
 *
 * R34: the test must execute the packaged program and verify it works.
 * A small C driver invokes `captagent -v` and `captagent -h` and asserts
 * rc==0 plus expected output markers (version string, usage text).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_and_check(const char *arg, const char *needle) {
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "captagent %s 2>&1", arg);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "captagent_test: popen failed for '%s'\n", cmd);
        return 1;
    }

    char buf[4096];
    int found = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, needle)) {
            found = 1;
        }
    }
    int rc = pclose(fp);

    if (!found) {
        fprintf(stderr, "captagent_test: output of 'captagent %s' missing marker '%s'\n",
                arg, needle);
        return 1;
    }
    if (rc != 0) {
        fprintf(stderr, "captagent_test: 'captagent %s' exit status %d\n", arg, rc);
        return 1;
    }
    printf("captagent_test: OK  'captagent %s' -> contains '%s'\n", arg, needle);
    return 0;
}

int main(void) {
    int fails = 0;

    /* -v prints "version: 6.4.4" */
    fails += run_and_check("-v", "6.4.4");

    /* -h prints usage text mentioning the config file option */
    fails += run_and_check("-h", "-f");

    if (fails) {
        fprintf(stderr, "captagent_test: %d check(s) failed\n", fails);
        return 1;
    }
    printf("captagent_test: all checks passed\n");
    return 0;
}
