/*
 * test.c — algol68g test_package smoke test.
 *
 * algol68g is a compiler-interpreter (not a library), so this test verifies
 * the a68g binary can execute a minimal Algol 68 program via --execute and
 * produce the expected output. We avoid stdin heredoc because Conan's
 * self.run() on OHOS may not have a usable stdin attached.
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
    char cmd[1024];
    FILE *p;
    char out[128];
    size_t n;

    /* Run a minimal Algol 68 program: print((1+1)) should yield +2 */
    snprintf(cmd, sizeof(cmd), "a68g --execute 'print((1+1))' 2>&1");

    p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: cannot run a68g\n");
        return 1;
    }
    n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    if (pclose(p) != 0) {
        fprintf(stderr, "FAIL: a68g invocation returned non-zero exit\n");
        return 1;
    }

    if (strstr(out, "+2") == NULL) {
        fprintf(stderr, "FAIL: unexpected a68g output: %s\n", out);
        return 1;
    }

    printf("PASS: a68g executed Algol 68 program, output: %s", out);
    return 0;
}
