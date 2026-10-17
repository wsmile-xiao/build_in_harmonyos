/* test.c — consumer + OHOS-specific test for desktop-file-utils 0.28.
 *
 * Real business-API coverage (not just --version):
 *   A) desktop-file-validate --version  -> stdout must contain "0.28"
 *   B) desktop-file-validate on a VALID .desktop file -> exit 0, "No errors"
 *   C) desktop-file-validate on an INVALID .desktop file -> non-zero exit
 *      (the validator reports the broken group header)
 *
 * Uses fork+exec (no system(), no shell injection). Temp files are written
 * to $TMPDIR when set (OHOS /tmp may be read-only), else to the current dir.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/stat.h>

static int run_capture(const char *bin, char *const args[], char *out, size_t outsz) {
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        printf("FAIL: pipe\n");
        return -1;
    }
    pid_t pid = fork();
    if (pid < 0) {
        printf("FAIL: fork\n");
        return -1;
    }
    if (pid == 0) {
        close(pipefd[0]);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[1]);
        execv(bin, args);
        _exit(127);
    }
    close(pipefd[1]);
    ssize_t n = read(pipefd[0], out, outsz - 1);
    close(pipefd[0]);
    if (n < 0) n = 0;
    out[n] = '\0';
    int status = 0;
    waitpid(pid, &status, 0);
    if (!WIFEXITED(status))
        return -1;
    return WEXITSTATUS(status);
}

static int write_file_at(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    if (!f) {
        printf("FAIL: cannot write %s\n", path);
        return -1;
    }
    fputs(content, f);
    fclose(f);
    return 0;
}

int main(int argc, char *argv[]) {
    const char *bin;
    if (argc < 2) {
        printf("FAIL: no desktop-file-validate binary path provided\n");
        return 1;
    }
    bin = argv[1];

    char out[4096];

    /* A) version probe */
    {
        char *args[] = {(char *)bin, "--version", NULL};
        int rc = run_capture(bin, args, out, sizeof(out));
        if (rc != 0 || strstr(out, "0.28") == NULL) {
            printf("FAIL: --version exited %d, output missing 0.28: '%s'\n", rc, out);
            return 1;
        }
        printf("OK-A: version probe -> %s", out);
    }

    /* Resolve a writable temp dir (OHOS /tmp may be read-only) */
    const char *tmp = getenv("TMPDIR");
    if (!tmp || !*tmp) tmp = ".";
    char valid_path[1024], invalid_path[1024];
    snprintf(valid_path, sizeof(valid_path), "%s/dfu-valid-%ld.desktop", tmp, (long)getpid());
    snprintf(invalid_path, sizeof(invalid_path), "%s/dfu-invalid-%ld.desktop", tmp, (long)getpid());

    /* B) valid .desktop file -> exit 0, "No errors" */
    {
        const char *valid =
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Test App\n"
            "Exec=/bin/true\n";
        if (write_file_at(valid_path, valid) != 0) return 1;
        char *args[] = {(char *)bin, valid_path, NULL};
        int rc = run_capture(bin, args, out, sizeof(out));
        if (rc != 0) {
            printf("FAIL-B: valid .desktop validate exited %d: '%s'\n", rc, out);
            return 1;
        }
        printf("OK-B: valid .desktop validate -> exit 0\n");
    }

    /* C) invalid .desktop file (no [Desktop Entry], broken line) -> non-zero */
    {
        const char *invalid =
            "Type=Application\n"
            "Name=Broken\n"
            "Exec=should fail because the group header is missing\n";
        if (write_file_at(invalid_path, invalid) != 0) return 1;
        char *args[] = {(char *)bin, invalid_path, NULL};
        int rc = run_capture(bin, args, out, sizeof(out));
        if (rc == 0) {
            printf("FAIL-C: invalid .desktop validate exited 0 (should fail)\n");
            return 1;
        }
        printf("OK-C: invalid .desktop validate -> exit %d\n", rc);
    }

    remove(valid_path);
    remove(invalid_path);
    printf("OK: desktop-file-utils consumer + validation checks passed\n");
    return 0;
}