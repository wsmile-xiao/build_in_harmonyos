#include <stdio.h>
#include <pcp/pmapi.h>

/*
 * L1 consumer test for PCP on OHOS.
 *
 * Uses pmErrStr() — a context-free PMDA utility (no running pmcd or
 * archive needed), so it is reliable in the CI/offline environment.
 * The upstream qa/ suite (make check) requires a live pmcd + PMDAs and
 * is declared in MANIFEST.yml (not run in CI).
 */
int main(void) {
    const char *s = pmErrStr(0);
    if (s == NULL || s[0] == '\0') {
        fprintf(stderr, "FAIL: pmErrStr(0) returned NULL/empty\n");
        return 1;
    }
    printf("pcp 7.1.5 L1 test OK: pmErrStr(0)=\"%s\"\n", s);
    return 0;
}
