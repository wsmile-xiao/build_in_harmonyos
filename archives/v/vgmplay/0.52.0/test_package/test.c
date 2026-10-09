/* Functional consumer test: locate vgmplay via CMakeDeps-provided bin dir
 * (passed as argv[1] from CMakeLists) and assert the packaged CLI actually
 * runs and reports the right version. */
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    char cmd[1024];
    if (argc < 2) {
        printf("FAIL: no vgmplay bin dir provided\n");
        return 1;
    }
    /* Run the packaged binary by absolute path (bindirs on PATH not required). */
    snprintf(cmd, sizeof(cmd), "\"%s/vgmplay\" --version | grep -q 'VGMPlay 0.52.0'", argv[1]);
    if (system(cmd) != 0) {
        printf("FAIL: vgmplay --version did not report 0.52.0 (bin=%s)\n", argv[1]);
        return 1;
    }
    printf("test vgmplay 0.52.0: consumer --version check OK (bin=%s)\n", argv[1]);
    return 0;
}
