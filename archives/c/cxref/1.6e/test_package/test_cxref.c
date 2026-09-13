/* test_cxref.c — drive the installed cxref binary through real jobs and
 * assert actual behaviour (R34):
 *
 *   1. -html on a sample C file -> exit 0, sample.c.html generated and
 *      contains the cross-referenced function name
 *   2. unknown option --version -> exit 1, usage banner contains the
 *      upstream version string "Version 1.6e"
 *   3. missing input file -> stderr contains "Cannot access the file"
 *      (upstream exits 0 even for this error; the message is the
 *      observable behaviour, asserted as-is)
 *
 * Runs in the test working directory; the package's bin/ is on the PATH
 * from the conanrun environment, so the cxref wrapper finds its bundled
 * cxref-cpp preprocessor.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

#define SAMPLE_PROG "int add(int a, int b) { return a+b; }\n" \
                    "int main(void) { return add(1,2); }\n"

struct result {
    int exit_code;
    char output[8192];
};

static int failures = 0;

static struct result run_cxref(const char *bin, const char *args) {
    struct result r;
    char cmd[4096];
    snprintf(cmd, sizeof cmd, "\"%s\" %s 2>&1", bin, args);
    r.exit_code = -1;
    r.output[0] = '\0';

    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: popen(%s)\n", cmd);
        failures++;
        return r;
    }
    size_t n = fread(r.output, 1, sizeof r.output - 1, p);
    r.output[n] = '\0';
    int status = pclose(p);
    if (WIFEXITED(status))
        r.exit_code = WEXITSTATUS(status);
    return r;
}

static char *read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    static char buf[16384];
    size_t n = fread(buf, 1, sizeof buf - 1, f);
    buf[n] = '\0';
    fclose(f);
    return buf;
}

static void check(int cond, const char *what) {
    if (cond)
        printf("PASS: %s\n", what);
    else {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <cxref-binary>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    struct result r;

    /* Sample C file with one function to cross-reference. */
    FILE *f = fopen("sample.c", "w");
    if (!f) {
        fprintf(stderr, "FAIL: cannot create sample.c\n");
        return 1;
    }
    fputs(SAMPLE_PROG, f);
    fclose(f);

    /* 1. HTML cross reference generation. */
    r = run_cxref(bin, "-html sample.c");
    check(r.exit_code == 0, "cxref -html exits 0");
    {
        char *html = read_file("sample.c.html");
        check(html != NULL, "cxref -html generates sample.c.html");
        check(html != NULL && strstr(html, "add") != NULL,
              "cxref html output references the function add");
    }

    /* 2. Unknown option: usage banner carries the version. */
    r = run_cxref(bin, "--version");
    check(r.exit_code == 1, "cxref with an unknown option exits 1");
    check(strstr(r.output, "Version 1.6e") != NULL,
          "cxref usage banner reports version 1.6e");

    /* 3. Missing input file: observable error message. */
    r = run_cxref(bin, "-html nosuchfile.c");
    check(strstr(r.output, "Cannot access the file") != NULL,
          "cxref reports the inaccessible input file");

    remove("sample.c");
    remove("sample.c.html");
    remove("cxref.html");
    remove("cxref.css");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("all cxref behaviour checks passed\n");
    return 0;
}
