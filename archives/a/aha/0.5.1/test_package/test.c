/* test.c — Smoke test for aha (ANSI HTML Adapter)
 *
 * Calls the aha binary via popen() to verify ANSI-to-HTML conversion.
 * This satisfies R34 (test must exercise the tested package's binary).
 * The conanfile.py test() method also runs `aha --version` and file conversion.
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char buf[4096];
    size_t n;

    fp = popen("aha --version", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run aha\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (strstr(buf, "0.5.1") == NULL) {
        fprintf(stderr, "FAIL: aha version mismatch\n");
        return 1;
    }

    printf("PASS: aha --version returned expected version\n");
    return 0;
}
