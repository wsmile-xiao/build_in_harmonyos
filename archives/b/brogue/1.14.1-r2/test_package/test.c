#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    /* Verify brogue binary exists and is executable via access() */
    if (access("brogue", X_OK) != 0) {
        /* Fallback: try PATH lookup, decode wait status with WEXITSTATUS */
        int rc = system("which brogue > /dev/null 2>&1");
        if (rc == -1 || !WIFEXITED(rc) || WEXITSTATUS(rc) != 0) {
            printf("FAIL: brogue binary not found\n");
            return 1;
        }
    }
    /* Execute brogue to verify it actually runs; decode wait status with WEXITSTATUS */
    int rc = system("brogue --version 2>&1 || brogue --help 2>&1 || brogue -h 2>&1");
    if (rc != -1 && WIFEXITED(rc) && WEXITSTATUS(rc) == 0) {
        printf("test brogue 1.14.1-r2: OK\n");
        return 0;
    }
    printf("FAIL: brogue binary found but execution failed (rc=%d)\n", rc);
    return 1;
}
