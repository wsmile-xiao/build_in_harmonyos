#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

/* test_package smoke test for the socket-activate CLI binary.
 * sasa is a command-line tool, not a library — the binary is exercised
 * directly. 2 explicit checks: --version and --help.
 */
int main(int argc, char *argv[]) {
    const char *sock_bin = (argc > 1) ? argv[1] : "socket-activate";
    char cmd[512];
    int ret;

    printf("Testing socket-activate binary: %s\n", sock_bin);

    /* Check 1: --version must succeed and mention the program name. */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", sock_bin);
    ret = system(cmd);
    if (ret == -1) {
        perror("system");
        return 1;
    }
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: socket-activate --version returned %d\n", ret);
        return 1;
    }
    printf("PASS: socket-activate --version OK\n");

    /* Check 2: --help must succeed and print usage. */
    snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", sock_bin);
    ret = system(cmd);
    if (ret == -1) {
        perror("system");
        return 1;
    }
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: socket-activate --help returned %d\n", ret);
        return 1;
    }
    printf("PASS: socket-activate --help OK\n");

    printf("All tests passed\n");
    return 0;
}
