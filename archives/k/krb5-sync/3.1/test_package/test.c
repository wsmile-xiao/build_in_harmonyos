/* Consumer-side smoke test for krb5-sync: verify that the package installed a
 * runnable krb5-sync command and that it is not a stub.  The path is injected
 * by test_package/conanfile.py through KRBSYNC_BIN. */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void) {
    const char *bin = getenv("KRBSYNC_BIN");
    pid_t pid;
    int devnull, status = 0, code;

    if (bin == NULL || bin[0] == '\0') {
        fprintf(stderr, "KRBSYNC_BIN not set by test_package\n");
        return 2;
    }
    if (access(bin, X_OK) != 0) {
        perror("access(KRBSYNC_BIN)");
        return 1;
    }
    fflush(stdout);
    pid = fork();
    if (pid < 0) {
        perror("fork");
        return 2;
    }
    if (pid == 0) {
        devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) {
            dup2(devnull, 2);
            close(devnull);
        }
        execl(bin, bin, "--help", (char *) NULL);
        _exit(127);
    }
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 2;
    }
    if (!WIFEXITED(status)) {
        fprintf(stderr, "krb5-sync did not exit normally\n");
        return 1;
    }
    code = WEXITSTATUS(status);
    if (code == 126 || code == 127) {
        fprintf(stderr, "krb5-sync not runnable (rc=%d)\n", code);
        return 1;
    }
    printf("krb5-sync ran (rc=%d)\n", code);
    return 0;
}
