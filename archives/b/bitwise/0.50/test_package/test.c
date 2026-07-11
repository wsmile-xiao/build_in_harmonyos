#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    const char *bitwise_bin = (argc > 1) ? argv[1] : "bitwise";
    char cmd[512];
    int ret;

    printf("Testing bitwise binary: %s\n", bitwise_bin);

    /* Test 1: --version */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", bitwise_bin);
    ret = system(cmd);
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: bitwise --version returned %d\n", ret);
        return 1;
    }
    printf("PASS: bitwise --version OK\n");

    /* Test 2: --no-color 0xFF */
    snprintf(cmd, sizeof(cmd), "\"%s\" --no-color 0xFF 2>&1", bitwise_bin);
    ret = system(cmd);
    if (!WIFEXITED(ret) || WEXITSTATUS(ret) != 0) {
        fprintf(stderr, "FAIL: bitwise --no-color 0xFF returned %d\n", ret);
        return 1;
    }
    printf("PASS: bitwise --no-color 0xFF OK\n");

    printf("All tests passed\n");
    return 0;
}
