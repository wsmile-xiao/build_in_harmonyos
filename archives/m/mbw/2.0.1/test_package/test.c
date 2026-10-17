#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Test driver for mbw (Memory Bandwidth Benchmark) on OHOS.
 *
 * We cannot easily parse mbw's output portably across musl/toybox
 * environments, so the test simply invokes the binary with a tiny
 * benchmark pass and verifies it exits 0 and prints expected markers.
 */
int main(int argc, char **argv) {
    /* Locate the mbw binary: CMake injects TEST_MBW_PATH as a compile-time
     * macro (target_compile_definitions). Fall back to "mbw" and rely on PATH. */
#ifdef TEST_MBW_PATH
    const char *mbw = TEST_MBW_PATH;
#else
    const char *mbw = "mbw";
#endif

    char cmd[512];
    snprintf(cmd, sizeof(cmd), "\"%s\" -n 1 1024", mbw);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "mbw_test: popen failed\n");
        return 1;
    }

    char buf[4096];
    size_t total = 0;
    int has_method = 0;
    int has_mib = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        total += strlen(buf);
        if (strstr(buf, "Method:")) has_method = 1;
        if (strstr(buf, "MiB")) has_mib = 1;
    }
    int rc = pclose(fp);

    if (rc != 0) {
        fprintf(stderr, "mbw_test: mbw exited rc=%d\n", rc);
        return 1;
    }
    if (!has_method && !has_mib) {
        fprintf(stderr, "mbw_test: no benchmark output detected\n");
        return 1;
    }
    printf("mbw_test: OK (%zu bytes output, method=%d mib=%d)\n",
           total, has_method, has_mib);
    return 0;
}
