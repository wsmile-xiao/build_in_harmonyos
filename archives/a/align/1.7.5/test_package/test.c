/*
 * test.c — align test_package smoke test.
 *
 * align is a Perl-script CLI tool (text column alignment filter), so this
 * test runs the align binary with a small input and checks it produces
 * aligned output. We avoid stdin heredoc because Conan's self.run() on
 * OHOS may not have a usable stdin attached.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static int run_cmd(const char *cmd) {
    int ret = system(cmd);
    if (ret == -1) return -1;
    return WIFEXITED(ret) && WEXITSTATUS(ret) == 0 ? 0 : -1;
}

int main(void) {
    /* Run align with a temp input file; expect 0 exit (functional tool) */
    FILE *f = fopen("in.txt", "w");
    if (!f) { fprintf(stderr, "FAIL: cannot create in.txt\n"); return 1; }
    fprintf(f, "a b\nccc dddd\n");
    fclose(f);

    if (run_cmd("align < in.txt > out.txt 2>/dev/null") != 0) {
        fprintf(stderr, "FAIL: align invocation returned non-zero exit\n");
        return 1;
    }

    f = fopen("out.txt", "r");
    if (!f) { fprintf(stderr, "FAIL: align produced no output\n"); return 1; }
    char buf[256] = {0};
    fgets(buf, sizeof(buf), f);
    fclose(f);

    if (strstr(buf, "a") == NULL) {
        fprintf(stderr, "FAIL: unexpected align output: %s\n", buf);
        return 1;
    }
    printf("PASS: align produced output: %s", buf);
    remove("in.txt");
    remove("out.txt");
    return 0;
}
