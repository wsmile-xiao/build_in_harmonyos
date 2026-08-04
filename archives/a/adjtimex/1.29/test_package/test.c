/* test.c — Smoke test for adjtimex 1.29
 *
 * Upstream adjtimex has no official test suite. R34 requires the test to
 * exercise the tested package's binary. `adjtimex --version` is the only
 * CLI path that does not invoke the adjtimex() syscall (blocked by the
 * OHOS seccomp sandbox with SIGSYS), so it is used as the smoke test.
 * The conanfile.py test() method also runs `adjtimex --version`.
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char buf[256];
    size_t n;

    fp = popen("adjtimex --version 2>/dev/null", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run adjtimex\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (strstr(buf, "adjtimex 1.29") == NULL) {
        fprintf(stderr, "FAIL: adjtimex version mismatch, got: %s\n", buf);
        return 1;
    }

    printf("PASS: adjtimex --version returned expected version\n");
    return 0;
}
