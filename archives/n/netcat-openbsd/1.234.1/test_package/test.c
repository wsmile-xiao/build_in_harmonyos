/* test.c — Smoke test for netcat-openbsd 1.234.1
 *
 * R34 requires the test to exercise the tested package's binary.
 * netcat-openbsd is a CLI tool with no library API, so we run `nc -h`
 * via popen() and verify the output contains expected usage text.
 *
 * The conanfile.py test() method also runs `nc -h` directly.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void) {
    FILE *fp;
    char buf[512];
    size_t n;

    fp = popen("nc -h 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run nc\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (n == 0) {
        fprintf(stderr, "FAIL: nc -h produced no output\n");
        return 1;
    }

    /* nc -h should print usage text containing "usage" */
    if (strstr(buf, "usage") == NULL) {
        fprintf(stderr, "FAIL: nc -h output does not contain 'usage': %s\n", buf);
        return 1;
    }

    printf("PASS: nc -h returned expected usage text\n");
    return 0;
}
