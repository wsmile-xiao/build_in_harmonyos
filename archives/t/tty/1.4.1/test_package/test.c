#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Consumer test: execute the packaged ttysolitaire binary end-to-end.
   Binary path passed as argv[1] (from conan package, avoids PATH dependency).
   Uses popen() to capture output — no temp files (conan env /tmp may be RO). */

static int run_check(const char *bin, const char *arg,
                     const char *exact_line, const char *contains) {
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "\"%s\" %s 2>&1", bin, arg);
    FILE *f = popen(cmd, "r");
    if (!f) {
        return 0;
    }
    char buf[1024] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, f);
    buf[n] = '\0';
    int ret = pclose(f);
    if (ret != 0) {
        return 0;
    }
    if (exact_line) {
        return strcmp(buf, exact_line) == 0;
    }
    return strstr(buf, contains) != NULL;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL: no ttysolitaire binary path provided\n");
        return 1;
    }
    const char *bin = argv[1];

    /* Case C-1: `ttysolitaire -v` must exit 0 and print exactly "1.4.1". */
    if (!run_check(bin, "-v", "1.4.1\n", NULL)) {
        printf("FAIL: ttysolitaire -v output unexpected\n");
        return 1;
    }

    /* Case C-2: `ttysolitaire -h` must exit 0 and print usage. */
    if (!run_check(bin, "-h", NULL, "usage")) {
        printf("FAIL: ttysolitaire -h output unexpected\n");
        return 1;
    }

    printf("test tty 1.4.1: OK\n");
    return 0;
}
