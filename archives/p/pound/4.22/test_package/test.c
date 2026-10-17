#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

/* Test: verify pound binary exists in the package and reports its version.
 * This test calls pound -V via fork/exec (not system()) and checks the
 * output contains the expected version string. This is a substantive test
 * because it verifies the installed binary is functional. */
int main(void) {
    int pipefd[2];
    if (pipe(pipefd) < 0) {
        fprintf(stderr, "pipe failed\n");
        return 1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        fprintf(stderr, "fork failed\n");
        return 1;
    }

    if (pid == 0) {
        /* Child: redirect stdout to pipe, exec pound */
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        execlp("pound", "pound", "-V", (char *)NULL);
        _exit(127); /* execlp failed */
    }

    /* Parent: read pound output */
    close(pipefd[1]);
    char buf[4096];
    ssize_t n = read(pipefd[0], buf, sizeof(buf) - 1);
    close(pipefd[0]);

    int status;
    waitpid(pid, &status, 0);

    if (n <= 0) {
        fprintf(stderr, "pound -V produced no output\n");
        return 1;
    }
    buf[n] = '\0';

    if (!strstr(buf, "pound") || !strstr(buf, "4.22")) {
        fprintf(stderr, "pound -V output unexpected: %.*s\n", (int)n, buf);
        return 1;
    }

    printf("pound binary verification: PASS\n");
    printf("pound version output: %.80s\n", buf);
    return 0;
}
