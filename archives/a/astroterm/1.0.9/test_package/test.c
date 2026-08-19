#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    const char *astroterm_bin = (argc > 1) ? argv[1] : "astroterm";
    char cmd[512];
    int ret;

    printf("Testing astroterm binary: %s\n", astroterm_bin);

    /* Test 1: --version */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", astroterm_bin);
    ret = system(cmd);
    if (ret == -1) {
        perror("system");
        return 1;
    }
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: astroterm --version returned %d\n", ret);
        return 1;
    }
    printf("PASS: astroterm --version OK\n");

    /* Test 2: --help */
    snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", astroterm_bin);
    ret = system(cmd);
    if (ret == -1) {
        perror("system");
        return 1;
    }
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: astroterm --help returned %d\n", ret);
        return 1;
    }
    printf("PASS: astroterm --help OK\n");

    printf("All tests passed\n");
    return 0;
}
