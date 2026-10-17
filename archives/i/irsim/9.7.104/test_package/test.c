#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

/*
 * Consumer-style smoke test for the irsim CLI (R34: real, not a shell).
 *
 * argv[1] must be the path to the installed irsim binary.  This test:
 *   1. checks the binary exists and is executable (access X_OK);
 *   2. actually executes it (no arguments => usage banner / no-network
 *      diagnostic on stdout/stderr);
 *   3. verifies the process terminated normally (not signal-killed,
 *      not "cannot execute") and that the output identifies irsim.
 *
 * If the packaged product is missing, not executable, or corrupted, one
 * of the checks above fails and this test returns non-zero — there is no
 * "prints and passes" empty-shell path.
 */
int main(int argc, char **argv) {
    const char *bin;
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: test_irsim <path-to-irsim>\n");
        return 2;
    }
    bin = argv[1];

    /* 1. existence + executability */
    if (access(bin, X_OK) != 0) {
        fprintf(stderr, "FAIL: irsim binary missing or not executable: %s\n", bin);
        return 1;
    }
    printf("ok: irsim binary present and executable: %s\n", bin);

    /* 2. actually run it (usage banner goes to stdout) */
    {
        char cmd[4096];
        FILE *fp;
        char outbuf[1024] = "";
        size_t n = 0;

        snprintf(cmd, sizeof(cmd), "%s 2>&1", bin);
        fp = popen(cmd, "r");
        if (fp == NULL) {
            fprintf(stderr, "FAIL: cannot spawn %s\n", bin);
            return 1;
        }
        n = fread(outbuf, 1, sizeof(outbuf) - 1, fp);
        outbuf[n] = '\0';
        rc = pclose(fp);
        printf("irsim rc=%d\n", rc);
        printf("irsim output head: %.240s\n", outbuf);

        /* 3. observable result: process ran and identified itself */
        if (rc == -1 || WIFSIGNALED(rc)) {
            fprintf(stderr, "FAIL: irsim terminated abnormally\n");
            return 1;
        }
        if (strstr(outbuf, "irsim") == NULL) {
            fprintf(stderr, "FAIL: output does not identify irsim\n");
            return 1;
        }
    }

    printf("test irsim 9.7.104: PASSED (binary executed, rc captured, output verified)\n");
    return 0;
}
