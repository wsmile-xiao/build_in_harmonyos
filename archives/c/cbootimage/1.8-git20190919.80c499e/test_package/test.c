#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    /* test_package must actually exercise the packaged binary (R34):
       run `cbootimage` without arguments and expect its usage/error output. */
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s", "cbootimage");
    FILE *fp = popen(cmd, "r");
    if (fp == NULL) {
        fprintf(stderr, "cbootimage: FAILED to spawn\n");
        return 1;
    }
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1 || n == 0) {
        fprintf(stderr, "cbootimage: FAILED (no output, rc=%d)\n", rc);
        return 1;
    }
    /* Expect a usage/error line mentioning "Usage: cbootimage" */
    if (strstr(buf, "Usage: cbootimage") == NULL) {
        fprintf(stderr, "cbootimage: unexpected output: %s\n", buf);
        return 1;
    }
    printf("cbootimage test_package: OK (output: %s)\n", buf);
    return 0;
}
