#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    /* Verify tty-clock binary runs and prints version.
       Binary path passed as argv[1] (from conan package, avoids PATH dependency). */
    if (argc < 2) {
        printf("FAIL: no tty-clock binary path provided\n");
        return 1;
    }
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "\"%s\" -v > /dev/null 2>&1", argv[1]);
    int ret = system(cmd);
    if (ret != 0) {
        printf("FAIL: tty-clock -v returned %d\n", ret);
        return 1;
    }
    printf("test tty-clock 2.3: OK\n");
    return 0;
}