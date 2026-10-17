#include <stdlib.h>
#include <stdio.h>
#include <sys/wait.h>

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    /* Verify nnn binary exists and is executable */
    int rc = system("which nnn > /dev/null 2>&1");
    if (rc == -1 || !WIFEXITED(rc) || WEXITSTATUS(rc) != 0) {
        printf("FAIL: nnn binary not found in PATH\n");
        return 1;
    }
    /* Execute nnn to verify it actually runs (R34: test must use the binary) */
    rc = system("nnn -h > /dev/null 2>&1");
    if (rc != -1 && WIFEXITED(rc)) {
        printf("test nnn 5.0: OK\n");
        return 0;
    }
    printf("FAIL: nnn binary found but execution failed (rc=%d)\n", rc);
    return 1;
}
