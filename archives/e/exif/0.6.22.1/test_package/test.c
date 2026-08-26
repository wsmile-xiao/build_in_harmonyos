/* exif 0.6.22 consumer test (R34).
 *
 * exif is a command-line tool (no library), so this test verifies the
 * installed `exif` binary actually works:
 *   1. `exif --version`  — must print the version string (0.6.22)
 *   2. `exif` on a nonexistent file — must exit non-zero without crash
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int run_cmd(const char *const argv[], char *out, size_t outsz)
{
    int pipefd[2];
    if (pipe(pipefd) != 0)
        return -1;
    pid_t pid = fork();
    if (pid < 0) {
        return -1;
    }
    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);
        execvp(argv[0], (char *const *) argv);
        _exit(127);
    }
    close(pipefd[1]);
    size_t n = 0;
    while (n + 1 < outsz) {
        ssize_t r = read(pipefd[0], out + n, outsz - n - 1);
        if (r <= 0)
            break;
        n += (size_t) r;
    }
    close(pipefd[0]);
    out[n] = '\0';
    int status = 0;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return -1;
}

int main(void)
{
    char buf[512] = {0};

    /* 1. --version must succeed and print the version. */
    const char *v[] = {"exif", "--version", NULL};
    int rc = run_cmd(v, buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "exif --version failed (rc=%d): %s\n", rc, buf);
        return 1;
    }
    if (strstr(buf, "0.6.22") == NULL) {
        fprintf(stderr, "exif --version did not print 0.6.22: %s\n", buf);
        return 2;
    }

    /* 2. Missing file must fail cleanly (non-zero), not crash. */
    const char *m[] = {"exif", "/nonexistent/exif-test.jpg", NULL};
    rc = run_cmd(m, buf, sizeof(buf));
    if (rc == 0) {
        fprintf(stderr, "exif on missing file unexpectedly succeeded\n");
        return 3;
    }

    if (puts("exif CLI test: OK") == EOF)
        return 4;
    return 0;
}
