/* test.c — Consumer test for cfm (Cactus File Manager).
 *
 * Simulates a higher-layer component that launches the installed `cfm`
 * binary against a real directory. This exercises the runtime artifact:
 * the ELF must load and the directory scan must run on the target.
 * We cannot drive the interactive TUI from C portably here, so the pty
 * rendering check lives in conanfile.py's test() (Python pty module).
 */
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    /* Use a real writable scratch directory (root "/" makes cfm hang in
     * non-interactive mode on this platform). Prefer $TMPDIR, fall back to
     * /tmp — never hard-code a machine-specific absolute path. */
    const char *tmpbase = getenv("TMPDIR");
    if (tmpbase == NULL || *tmpbase == '\0') {
        tmpbase = "/tmp";
    }
    char scratch[PATH_MAX];
    snprintf(scratch, sizeof(scratch), "%s/cfm-cons-XXXXXX", tmpbase);
    if (mkdtemp(scratch) == NULL) {
        perror("mkdtemp");
        return 1;
    }
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 1;
    }
    if (pid == 0) {
        /* non-interactive run: closed stdin, quiet output */
        int devnull = open("/dev/null", O_RDONLY);
        if (devnull >= 0) {
            dup2(devnull, STDIN_FILENO);
        }
        char *argv[] = {"cfm", scratch, NULL};
        execvp("cfm", argv);
        perror("execvp cfm");
        _exit(127);
    }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 1;
    }
    rmdir(scratch);
    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
        fprintf(stderr, "FAIL: cfm consumer run status=%d\n", status);
        return 1;
    }
    printf("PASS: cfm binary launched and exited cleanly (rc=%d)\n",
           WEXITSTATUS(status));
    return 0;
}
