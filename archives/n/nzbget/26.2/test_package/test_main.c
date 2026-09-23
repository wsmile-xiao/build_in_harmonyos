#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34 consumer test: this program must exercise the package under test, not
 * print a canned string. nzbget ships only a CLI binary (no public library),
 * so the consumer executes the installed binary and asserts it reports its
 * version. Any exec/loader failure (format error, missing dependency) or a
 * missing "nzbget version" line fails the run.
 *
 * Usage: test_main <path-to-installed-nzbget-binary>
 */
int main(int argc, char **argv) {
    char cmd[1024];
    FILE *fp;
    char line[1024];
    int found = 0;

    if (argc != 2 || argv[1] == NULL) {
        fprintf(stderr, "test_main: usage: test_main <path-to-nzbget>\n");
        return 2;
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", argv[1]);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "test_main: cannot run \"%s\" (popen failed)\n", argv[1]);
        return 1;
    }

    /* Forward all output so a real loader/shell error stays visible in the
     * CI log, and require the version banner. */
    while (fgets(line, sizeof(line), fp) != NULL) {
        fputs(line, stdout);
        if (strstr(line, "nzbget version") != NULL) {
            found = 1;
        }
    }

    if (pclose(fp) != 0 || !found) {
        fprintf(stderr,
                "test_main: FAIL: `nzbget --version` did not report a "
                "\"nzbget version\" line (found=%d)\n",
                found);
        return 1;
    }
    return 0;
}
