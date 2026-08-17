/* test.c — consumer test for desktop-file-utils 0.28.
 *
 * Runs desktop-file-validate --version and asserts the output really
 * contains the expected version "0.28" (not just a nonzero exit code —
 * P3 fix: previously the version assertion was a no-op). Uses fork+exec
 * instead of system() to avoid shell-injection surface (P3 fix).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    /* Binary path passed as argv[1] (from conan package, avoids PATH dep) */
    if (argc < 2) {
        printf("FAIL: no desktop-file-validate binary path provided\n");
        return 1;
    }
    const char *bin = argv[1];

    /* Run `desktop-file-validate --version` and capture stdout via pipe */
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        printf("FAIL: pipe\n");
        return 1;
    }
    pid_t pid = fork();
    if (pid < 0) {
        printf("FAIL: fork\n");
        return 1;
    }
    if (pid == 0) {
        /* child: exec the binary directly (no shell, no injection) */
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);
        execl(bin, bin, "--version", (char *)NULL);
        _exit(127);
    }
    close(pipefd[1]);
    char out[1024];
    ssize_t n = read(pipefd[0], out, sizeof(out) - 1);
    close(pipefd[0]);
    if (n < 0) n = 0;
    out[n] = '\0';
    int status = 0;
    waitpid(pid, &status, 0);
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        printf("FAIL: %s --version exited %d\n", bin, WEXITSTATUS(status));
        return 1;
    }
    /* Real version assertion: output must contain "0.28" */
    if (strstr(out, "0.28") == NULL) {
        printf("FAIL: version output missing 0.28: '%s'\n", out);
        return 1;
    }
    printf("OK: desktop-file-utils 0.28 --version (%s)\n", out);
    return 0;
}
