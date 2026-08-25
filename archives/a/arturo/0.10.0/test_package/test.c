#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef ARTURO_BIN
#define ARTURO_BIN ""
#endif

/* R34: Test that the arturo binary actually works.
 * This test executes `arturo --version` via popen and verifies
 * the output contains "arturo" and "0.10.0".
 * The binary path is passed as a compile definition from CMakeLists.txt,
 * which gets it from Conan's dependency info (not hardcoded paths).
 */
int main(void) {
    const char *arturo_bin = ARTURO_BIN;
    if (!arturo_bin || strlen(arturo_bin) == 0) {
        fprintf(stderr, "FAIL: arturo binary path not provided\n");
        return 1;
    }

    char cmd[512];
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", arturo_bin);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot execute arturo binary at %s\n", arturo_bin);
        return 1;
    }

    char buf[256];
    int found_arturo = 0;
    int found_version = 0;
    while (fgets(buf, sizeof(buf), fp)) {
        if (strstr(buf, "arturo") != NULL) found_arturo = 1;
        if (strstr(buf, "0.10.0") != NULL) found_version = 1;
        printf("%s", buf);
    }
    pclose(fp);

    if (found_arturo && found_version) {
        printf("test arturo 0.10.0: OK\n");
        return 0;
    }

    fprintf(stderr,
            "FAIL: arturo version output not as expected "
            "(found arturo=%d, found version=%d)\n",
            found_arturo, found_version);
    return 1;
}
