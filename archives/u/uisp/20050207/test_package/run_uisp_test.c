/* Consumer test for uisp/20050207: launches the packaged `uisp` binary
 * and verifies it reports its version (R34: actually exercises the package). */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const char *bindir = getenv("UISP_BIN_DIR");
    char cmd[512];
    if (!bindir) {
        fprintf(stderr, "UISP_BIN_DIR not set\n");
        return 1;
    }
    snprintf(cmd, sizeof(cmd), "\"%s/uisp\" --version", bindir);
    int rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "uisp --version failed, rc=%d\n", rc);
        return 1;
    }
    printf("test uisp 20050207: OK\n");
    return 0;
}
