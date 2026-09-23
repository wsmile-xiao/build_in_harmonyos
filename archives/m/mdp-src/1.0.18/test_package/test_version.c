/*
 * Consumer test for mdp-src: compile a real client that drives the installed
 * mdp binary's non-interactive paths and asserts observable behaviour.
 *   1. `mdp -v` must exit 0 and print the exact "mdp 1.0.18" version banner;
 *   2. a missing input file must exit non-zero (error path).
 * Exit code of this program decides the test result.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    /* 1. version banner */
    FILE *p = popen("mdp -v 2>&1", "r");
    if (!p) {
        fprintf(stderr, "popen(mdp -v) failed\n");
        return 2;
    }
    char buf[512] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, p);
    (void)n;
    int rc = pclose(p);
    if (rc != 0) {
        fprintf(stderr, "mdp -v exited non-zero: %d\n", rc);
        return 1;
    }
    if (!strstr(buf, "mdp 1.0.18")) {
        fprintf(stderr, "version banner mismatch, got:\n%s\n", buf);
        return 1;
    }

    /* 2. missing input file -> non-zero exit */
    rc = system("mdp ./no-such-file.md > /dev/null 2>&1");
    if (rc == 0) {
        fprintf(stderr, "mdp accepted a missing input file (exit 0)\n");
        return 1;
    }

    printf("mdp consumer test OK\n");
    return 0;
}
