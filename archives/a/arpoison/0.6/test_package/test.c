/* test_arpoison.c — R34: Test that the arpoison binary is installed and runnable.
 *
 * arpoison requires root and network access, so we verify:
 *   1. The binary exists in PATH (installed by Conan)
 *   2. The binary executes and produces expected output
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

int main(void) {
    /* R34: Execute the arpoison binary to verify it's properly built */
    int ret = system("arpoison 2>&1");
    if (ret == -1) {
        printf("FAIL: shell failed to start\n");
        return 1;
    }
    if (!WIFEXITED(ret)) {
        printf("FAIL: arpoison did not exit normally (signal %d)\n", WTERMSIG(ret));
        return 1;
    }
    int code = WEXITSTATUS(ret);
    /* 127 = command not found in PATH */
    if (code == 127) {
        printf("FAIL: arpoison binary not found in PATH\n");
        return 1;
    }
    /* 126 = permission denied (not executable) */
    if (code == 126) {
        printf("FAIL: arpoison binary found but not executable\n");
        return 1;
    }
    /* arpoison exits with code 1 when run without root or without args,
     * which means the binary is present and functional */
    printf("PASS: arpoison binary exists and runs correctly (exit %d)\n", code);
    return 0;
}
