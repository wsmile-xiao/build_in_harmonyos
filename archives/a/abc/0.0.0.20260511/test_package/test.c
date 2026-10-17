/*
 * test.c — abc test_package smoke test.
 *
 * abc is a command-line tool (logic synthesis), not a library, so this
 * test verifies the abc binary is callable and can run a simple command
 * via `abc -c "version"`, checking the expected banner output.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    FILE *p;
    char out[512];
    size_t n;

    /* Run abc with the "version" command */
    p = popen("abc -c 'version' 2>&1", "r");
    if (!p) {
        fprintf(stderr, "FAIL: cannot run abc\n");
        return 1;
    }
    n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    if (pclose(p) != 0) {
        fprintf(stderr, "FAIL: abc invocation returned non-zero exit\n");
        return 1;
    }

    if (strstr(out, "UC Berkeley, ABC") == NULL) {
        fprintf(stderr, "FAIL: unexpected abc output: %s\n", out);
        return 1;
    }

    printf("PASS: abc ran version command, output: %.60s\n", out);
    return 0;
}
