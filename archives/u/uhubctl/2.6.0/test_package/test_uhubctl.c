/* test_uhubctl.c — test_package for uhubctl 2.6.0 (R34).
 *
 * uhubctl is a CLI tool, not a library, so the consumer test executes the
 * packaged binary and asserts on its real behavior:
 *
 *   1. uhubctl -v      → prints the program version "2.6.0", exit 0
 *   2. uhubctl -h      → prints the usage banner, which mentions --version
 *   3. uhubctl         → USB bus listing; with no smart hubs attached the
 *                        program must still link/run against libusb-1.0 and
 *                        terminate cleanly (exit code 0 or 1, no signal)
 *
 * The binary path is passed as argv[1] by test_package/conanfile.py, so the
 * test fails (exec failure) when the package artifacts are removed —
 * required by the CI L1e destructive negative test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static const char *uhubctl_bin = NULL;
static int failures = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

/* Run uhubctl with the given argv, capture stdout+stderr, return exit status.
 * out buffer (if non-NULL) receives the first (size-1) bytes of the output. */
static int run_uhubctl(char *const argv[], char *out, size_t outsz)
{
    int pipefd[2];
    if (pipe(pipefd) != 0)
        return -1;
    pid_t pid = fork();
    if (pid < 0) {
        close(pipefd[0]);
        close(pipefd[1]);
        return -1;
    }
    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO); /* usage/diagnostics go to stderr */
        close(pipefd[1]);
        execv(uhubctl_bin, argv);
        _exit(127); /* exec failed — binary missing/broken */
    }
    close(pipefd[1]);
    if (out) {
        size_t got = 0;
        ssize_t n;
        while (got + 1 < outsz &&
               (n = read(pipefd[0], out + got, outsz - 1 - got)) > 0)
            got += (size_t)n;
        out[got] = '\0';
    }
    close(pipefd[0]);
    int status = -1;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return -1; /* crashed by signal */
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <uhubctl-binary>\n", argv[0]);
        return 2;
    }
    uhubctl_bin = argv[1];

    /* 1. -v prints the exact program version and exits 0 */
    char *v_argv[] = {"uhubctl", "-v", NULL};
    char out[4096]; /* usage text is long; keep --version within reach */
    int rc = run_uhubctl(v_argv, out, sizeof(out));
    check(rc == 0, "uhubctl -v exits 0");
    check(strstr(out, "2.6.0") != NULL, "uhubctl -v prints version 2.6.0");

    /* 2. -h prints the usage banner mentioning --version */
    char *h_argv[] = {"uhubctl", "-h", NULL};
    rc = run_uhubctl(h_argv, out, sizeof(out));
    check(rc == 0 || rc == 1, "uhubctl -h terminates cleanly");
    check(strstr(out, "--version") != NULL, "usage text documents --version");

    /* 3. no-argument listing: runs against the real libusb-1.0 and exits
     * cleanly (0 when hubs listed, 1 when none found) — never a crash */
    char *l_argv[] = {"uhubctl", NULL};
    rc = run_uhubctl(l_argv, out, sizeof(out));
    check(rc == 0 || rc == 1, "uhubctl listing exits 0/1 without crash");
    check(strlen(out) > 0, "uhubctl listing produces diagnostic output");

    printf("---\n%d failure(s)\n", failures);
    return failures ? 1 : 0;
}
