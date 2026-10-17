#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/wait.h>

/* Run a command with output redirected to a file, then read the file and
 * check whether it contains `needle`.  Returns 0 on success, 1 on failure.
 * Uses file redirection instead of a pipe so the child (asy) never writes
 * to a closed pipe (SIGPIPE-safe on this platform). */
static int run_to_file(const char *cmd, const char *outfile, const char *needle)
{
    char shell_cmd[1400];
    snprintf(shell_cmd, sizeof(shell_cmd), "%s > %s 2>&1", cmd, outfile);

    int ret = system(shell_cmd);
    if (ret == -1) {
        fprintf(stderr, "system() failed for: %s\n", cmd);
        return 1;
    }
    int code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
    if (code != 0) {
        fprintf(stderr, "process exited with code %d: %s\n", code, cmd);
        return 1;
    }

    FILE *f = fopen(outfile, "r");
    if (f == NULL) {
        fprintf(stderr, "cannot read %s\n", outfile);
        return 1;
    }
    char buf[16384] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    buf[n] = '\0';
    fclose(f);

    if (needle != NULL && strstr(buf, needle) == NULL) {
        fprintf(stderr, "output did not contain '%s':\n%s\n", needle, buf);
        return 1;
    }
    return 0;
}

int main(void)
{
    const char *asy_bin = getenv("ASYMPTOTE_BIN");
    if (asy_bin == NULL || asy_bin[0] == '\0')
        asy_bin = "asy";

    char version_cmd[1200];
    snprintf(version_cmd, sizeof(version_cmd), "%s --version", asy_bin);

    /* 1) version probe: must identify "Asymptote version 3.12" */
    if (run_to_file(version_cmd, "version_check.txt",
                    "Asymptote version 3.12") != 0)
        return 1;

    /* 2) real render: draw an unlabeled box to EPS, no LaTeX needed.
     *    -render=0 avoids any GL dependency; -sysdir points at the packaged
     *    base modules (set via ASYMPTOTE_SYSDIR by the test harness). */
    const char *sysdir = getenv("ASYMPTOTE_SYSDIR");
    if (sysdir == NULL || sysdir[0] == '\0') {
        fprintf(stderr, "ASYMPTOTE_SYSDIR not set\n");
        return 1;
    }

    const char *asy_src =
        "size(100);\n"
        "draw(unitsquare);\n";
    const char *asy_file = "harness.asy";
    FILE *f = fopen(asy_file, "w");
    if (f == NULL) {
        fprintf(stderr, "cannot write %s\n", asy_file);
        return 1;
    }
    fputs(asy_src, f);
    fclose(f);

    char render_cmd[1400];
    snprintf(render_cmd, sizeof(render_cmd),
             "%s -render=0 -sysdir \"%s\" -o harness %s",
             asy_bin, sysdir, asy_file);
    /* render success is judged by exit code + non-empty EPS file below */
    if (run_to_file(render_cmd, "render_check.txt", NULL) != 0)
        return 1;

    /* rendered EPS must exist and be non-empty */
    FILE *eps = fopen("harness.eps", "rb");
    if (eps == NULL) {
        fprintf(stderr, "harness.eps was not produced\n");
        return 1;
    }
    if (fseek(eps, 0, SEEK_END) != 0 || ftell(eps) <= 0) {
        fprintf(stderr, "harness.eps is empty\n");
        fclose(eps);
        return 1;
    }
    fclose(eps);

    printf("PASS: asymptote 3.12 --version + EPS render ok\n");
    return 0;
}
