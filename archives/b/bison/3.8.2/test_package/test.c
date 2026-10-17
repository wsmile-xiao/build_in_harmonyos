/*
 * test.c — bison test_package smoke test.
 *
 * bison is a command-line tool (not a library), so this test verifies the
 * bison binary is callable and can parse a minimal grammar. We write a
 * minimal grammar to a temporary file and invoke bison on it, then check
 * the generated parser source is non-empty. We avoid stdin heredoc because
 * Conan's self.run() on OHOS may not have a usable stdin attached.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>

static int run_cmd(const char *cmd) {
    int ret = system(cmd);
    if (ret == -1) return -1;
    return WIFEXITED(ret) && WEXITSTATUS(ret) == 0 ? 0 : -1;
}

static int file_exists(const char *path) {
    struct stat st;
    return stat(path, &st) == 0 && st.st_size > 0 ? 0 : -1;
}

int main(void) {
    const char *in_path  = "test_minimal.y";
    const char *out_path = "test_y.tab.c";
    char cmd[1024];
    FILE *f;

    /* Write a minimal grammar to a temp file. */
    f = fopen(in_path, "w");
    if (!f) {
        fprintf(stderr, "FAIL: cannot create %s\n", in_path);
        return 1;
    }
    fprintf(f, "%s\nstart: ;\n%s\n", "%%", "%%");
    fclose(f);

    /* Run bison on the grammar file. */
    snprintf(cmd, sizeof(cmd), "bison -o %s %s", out_path, in_path);

    if (run_cmd(cmd) != 0) {
        fprintf(stderr, "FAIL: bison invocation returned non-zero exit\n");
        return 1;
    }

    if (file_exists(out_path) != 0) {
        fprintf(stderr, "FAIL: bison did not generate %s\n", out_path);
        return 1;
    }

    printf("PASS: bison generated parser source %s\n", out_path);

    /* Cleanup temp files (best-effort). */
    remove(in_path);
    remove(out_path);
    return 0;
}
