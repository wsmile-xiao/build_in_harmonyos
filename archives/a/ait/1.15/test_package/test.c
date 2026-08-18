/* test.c — Smoke test for ait (GNU Emacs style editor)
 *
 * Calls the ait binary via popen() to verify it executes and
 * reports the expected version. Satisfies R34 (test must
 * exercise the tested package's binary).
 */
#include <stdio.h>
#include <string.h>

int main(void) {
    FILE *fp;
    char buf[4096];
    size_t n;

    fp = popen("ait -v", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run ait\n");
        return 1;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    pclose(fp);

    if (strstr(buf, "1.15") == NULL) {
        fprintf(stderr, "FAIL: ait version mismatch (got: %s)\n", buf);
        return 1;
    }

    printf("PASS: ait -v returned expected version\n");
    return 0;
}
