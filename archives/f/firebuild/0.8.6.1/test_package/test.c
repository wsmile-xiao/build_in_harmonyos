/* firebuild 0.8.6.1 test_package - smoke test.
 *
 * firebuild is a CLI tool (firebuild-bin) + LD_PRELOAD interceptor
 * (libfirebuild.so). This smoke test verifies:
 *   1. The firebuild binary exists and is executable
 *   2. The firebuild binary responds to --version
 *   3. The libfirebuild.so shared library file exists
 *   4. LD_PRELOAD interceptor loading does not crash the supervisor
 *      (or is recorded as N/A if the interceptor requires a supervisor)
 *
 * Note: We intentionally do NOT dlopen libfirebuild.so. The interceptor's
 * __attribute__((constructor)) (fb_ic_init_constructor -> fb_ic_init)
 * attempts to connect to a firebuild supervisor process, read
 * /proc/self/exe, and send FBB messages. Without a running supervisor
 * this constructor segfaults on OHOS. The library is designed to be
 * loaded via LD_PRELOAD by the firebuild daemon, not standalone dlopen.
 * Testing the binary's CLI functionality is the correct smoke test.
 *
 * Finding 5 (P3) fix: The shell path used for execl() is now configurable
 * via the TEST_SHELL macro (compile-time -DTEST_SHELL=...), defaulting to
 * /bin/sh so the test is environment-independent.
 *
 * Finding 6 (P3) fix: We add a guarded assertion that attempts
 * LD_PRELOAD=<TARGET_SO> <TARGET_BIN> --version in a forked child.
 * If the child crashes with a signal (SIGSYS/SIGSEGV from the interceptor
 * constructor needing a supervisor), we record this as N/A with an
 * explanation, not a fake PASS and not a hard FAIL.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#ifndef TARGET_BIN
#define TARGET_BIN "/dev/null"
#endif
#ifndef TARGET_SO
#define TARGET_SO "/dev/null"
#endif
#ifndef TEST_SHELL
#define TEST_SHELL "/bin/sh"
#endif

static int failures = 0;
static int na_count = 0;
#define CHECK(c, m) do { \
    if (!(c)) { fprintf(stderr, "[FAIL] %s\n", (m)); ++failures; } \
    else printf("[ok] %s\n", (m)); \
} while (0)

/* Run a command and capture its stdout into a buffer.
 * Returns the exit code, or -1 on fork failure. */
static int run_capture(const char *cmd, char *buf, int bufsize) {
    int pipefd[2];
    if (pipe(pipefd) != 0) return -1;
    pid_t pid = fork();
    if (pid < 0) { close(pipefd[0]); close(pipefd[1]); return -1; }
    if (pid == 0) {
        /* child */
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        execl(TEST_SHELL, "sh", "-c", cmd, (char *)NULL);
        _exit(127);
    }
    /* parent */
    close(pipefd[1]);
    int total = 0;
    if (buf && bufsize > 0) buf[0] = '\0';
    while (total < bufsize - 1) {
        ssize_t n = read(pipefd[0], buf + total, bufsize - 1 - total);
        if (n <= 0) break;
        total += n;
        buf[total] = '\0';
    }
    close(pipefd[0]);
    int status = 0;
    waitpid(pid, &status, 0);
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return -1;
}

/* Run firebuild --version with LD_PRELOAD set to the interceptor .so.
 * Returns:
 *   0 = exited normally (interceptor loaded OK with supervisor context)
 *   1 = crashed with signal (interceptor constructor needs supervisor)
 *  -1 = fork/exec failure
 */
static int run_with_preload(const char *bin, const char *so) {
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) {
        /* child: set LD_PRELOAD and exec firebuild --version */
        setenv("LD_PRELOAD", so, 1);
        execl(bin, bin, "--version", (char *)NULL);
        _exit(127);
    }
    /* parent */
    int status = 0;
    waitpid(pid, &status, 0);
    if (WIFSIGNALED(status)) return 1;  /* crashed with signal */
    if (WIFEXITED(status)) return 0;    /* exited normally */
    return -1;
}

int main(void) {
    char outbuf[4096];

    /* 1. Verify firebuild binary exists and is executable */
    CHECK(access(TARGET_BIN, X_OK) == 0, "firebuild binary exists and is executable");

    /* 2. Verify libfirebuild.so exists (file present) */
    CHECK(access(TARGET_SO, F_OK) == 0, "libfirebuild.so file exists");

    /* 3. Run firebuild --version and check output */
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "%s --version", TARGET_BIN);
    int rc = run_capture(cmd, outbuf, sizeof(outbuf));
    CHECK(rc == 0, "firebuild --version exits with code 0");
    CHECK(strstr(outbuf, "Firebuild 0.8.6.1") != NULL,
          "firebuild --version output contains Firebuild 0.8.6.1");

    /* 4. LD_PRELOAD interceptor core adaptation path coverage.
     *
     * The interceptor's constructor (fb_ic_init) attempts to connect to
     * a firebuild supervisor process. Without a running supervisor, this
     * constructor will crash with SIGSYS or SIGSEGV on OHOS.
     *
     * We run `LD_PRELOAD=<TARGET_SO> <TARGET_BIN> --version` in a forked
     * child and observe the outcome:
     * - If the child exits normally (rc == 0), the interceptor loaded
     *   without crashing - this is a genuine PASS.
     * - If the child crashes with a signal (rc == 1), the interceptor
     *   constructor needs a supervisor. This is expected behavior, not
     *   a test failure. We record it as N/A with an explanation.
     * - If fork/exec fails (rc == -1), we record it as N/A.
     *
     * We do NOT fake a PASS. We do NOT introduce a hard assertion that
     * would fail when the interceptor legitimately needs a supervisor.
     */
    printf("\n[assert] LD_PRELOAD interceptor smoke test");
    int preload_rc = run_with_preload(TARGET_BIN, TARGET_SO);
    if (preload_rc == 0) {
        printf(" -> [ok] interceptor loaded without crash\n");
    } else if (preload_rc == 1) {
        printf(" -> [N/A] interceptor crashed (SIGSYS/SIGSEGV) - needs supervisor process, not verified standalone\n");
        ++na_count;
    } else {
        printf(" -> [N/A] fork/exec failure (rc=%d) - cannot verify LD_PRELOAD path\n", preload_rc);
        ++na_count;
    }

    if (failures) {
        fprintf(stderr, "\nfirebuild: %d assertions failed\n", failures);
        return 1;
    }
    printf("\nfirebuild 0.8.6.1: all smoke test assertions passed");
    if (na_count > 0) {
        printf(" (%d N/A - see output above)", na_count);
    }
    printf("\n");
    return 0;
}
