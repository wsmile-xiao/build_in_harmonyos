/*
 * Test driver for ekg2 (multi-protocol instant messenger) on OHOS.
 *
 * R34: the test must execute the packaged program and verify it works.
 * A small C driver invokes `ekg2 --help` and asserts rc==0 plus expected
 * help-text markers (program name and --version option).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
#ifdef TEST_EKG2_PATH
    const char *ekg2 = TEST_EKG2_PATH;
#else
    const char *ekg2 = "ekg2";
#endif
    /* find_program may resolve NOTFOUND/empty in cross-build; rely on conanrun PATH */
    if (!ekg2 || !*ekg2 || strstr(ekg2, "NOTFOUND")) {
        ekg2 = "ekg2";
    }

    char cmd[512];
    snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", ekg2);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "ekg2_test: popen failed\n");
        return 1;
    }

    char buf[4096];
    size_t total = 0;
    int has_help = 0;
    int has_version = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        total += strlen(buf);
        if (strstr(buf, "--help")) has_help = 1;
        if (strstr(buf, "--version")) has_version = 1;
    }
    int rc = pclose(fp);

    if (rc != 0) {
        fprintf(stderr, "ekg2_test: ekg2 --help exited rc=%d\n", rc);
        return 1;
    }
    if (total < 100) {
        fprintf(stderr, "ekg2_test: help output too short (%zu bytes)\n", total);
        return 1;
    }
    if (!has_help || !has_version) {
        fprintf(stderr, "ekg2_test: help output missing expected markers"
                " (help=%d version=%d)\n", has_help, has_version);
        return 1;
    }
    printf("ekg2_test: OK (%zu bytes output, help=%d version=%d)\n",
           total, has_help, has_version);
    return 0;
}
