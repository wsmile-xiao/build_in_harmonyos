#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

/* Test: verify mini_httpd and htpasswd binaries are installed and functional.
 * This is a consumer-side test (R34) that actually executes the packaged binaries.
 * commands.json declares both mini_httpd and htpasswd as deliverables,
 * so both must be smoke-tested to avoid shipping a broken htpasswd.
 */
int main(void) {
    int ret = system("mini_httpd -V");
    if (ret != 0) {
        fprintf(stderr, "FAIL: mini_httpd -V returned %d\n", ret);
        return 1;
    }
    printf("mini_httpd binary test: PASS\n");

    /* htpasswd with no args prints usage and exits non-zero.
     * We only need to confirm the binary exists and is executable;
     * a non-zero exit here means the binary ran (not missing/crashed).
     * system() returns the raw wait status (waitpid format), not the
     * raw exit code; use WIFEXITED/WEXITSTATUS macros to decode it.
     */
    ret = system("htpasswd 2>" "/dev/null");
    if (ret == 0) {
        /* Unexpected: htpasswd with no args should not succeed.
         * But if it does, the binary at least runs — treat as pass.
         */
        fprintf(stderr, "WARN: htpasswd returned 0 with no args\n");
    } else if (ret == -1) {
        /* -1 means fork/exec failed entirely (system() could not run shell). */
        fprintf(stderr, "FAIL: system() failed to execute htpasswd (ret=%d)\n", ret);
        return 1;
    } else if (WIFSIGNALED(ret)) {
        /* htpasswd was killed by a signal (e.g. SIGSEGV, SIGABRT). */
        fprintf(stderr, "FAIL: htpasswd killed by signal %d\n", WTERMSIG(ret));
        return 1;
    } else if (WIFEXITED(ret) && WEXITSTATUS(ret) == 127) {
        /* Shell exits 127 when command is not found in PATH.
         * WEXITSTATUS extracts the exit code from the waitpid status.
         */
        fprintf(stderr, "FAIL: htpasswd binary not found in PATH (exit 127)\n");
        return 1;
    } else if (WIFEXITED(ret) && WEXITSTATUS(ret) == 126) {
        /* Shell exits 126 when command found but not executable. */
        fprintf(stderr, "FAIL: htpasswd found but not executable (exit 126)\n");
        return 1;
    }
    printf("htpasswd binary test: PASS\n");
    return 0;
}
