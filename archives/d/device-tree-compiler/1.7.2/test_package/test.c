/* test.c — consumer test for device-tree-compiler 1.7.2.
 *
 * 1) Links against libfdt.a and calls fdt_magic()/fdt_check_header()
 *    to prove headers + static lib are usable (a zeroed buffer has no
 *    valid FDT_MAGIC, so fdt_check_header() must fail with
 *    FDT_ERR_BADMAGIC).
 * 2) Runs `fdtdump --version` via fork+exec (no shell) and asserts the
 *    output really contains "1.7.2".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#include <libfdt.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL: no fdtdump binary path provided\n");
        return 1;
    }
    const char *bin = argv[1];

    /* fdt_check_header() requires an 8-byte aligned buffer. */
    _Alignas(8) char buf[32];
    memset(buf, 0, sizeof(buf));
    fdt32_t magic = fdt_magic(buf);
    if (magic != 0) {
        printf("FAIL: fdt_magic on empty buffer = 0x%08x\n", (unsigned)magic);
        return 1;
    }
    int err = fdt_check_header(buf);
    if (err != -FDT_ERR_BADMAGIC) {
        printf("FAIL: fdt_check_header(empty) = %d (expected %d)\n", err, -FDT_ERR_BADMAGIC);
        return 1;
    }

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
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);
        execl(bin, bin, "--version", (char *)NULL);
        _exit(127);
    }
    close(pipefd[1]);
    char out[256];
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
    if (strstr(out, "1.7.2") == NULL) {
        printf("FAIL: version output missing 1.7.2: '%s'\n", out);
        return 1;
    }
    printf("OK: libfdt magic/header check + fdtdump --version (%s)", out);
    return 0;
}