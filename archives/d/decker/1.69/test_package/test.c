/*
 * test_package/test.c — decker 1.69 CMake/CTest smoke test.
 *
 * R34: real invocation of the installed lilt binary, not a stub.
 * lilt's CLI (see upstream c/lilt.c main()) supports:
 *   -h              print usage and exit 0
 *   -e EXPR         evaluate Lil expression EXPR and exit
 *   FILE.lil        execute a Lil source file and exit
 *   (no args)       enter interactive REPL
 *
 * There is NO --version flag: passing '--version' makes lilt treat it as
 * a filename, print "unable to open '--version'", and exit 0 — so a test
 * that only runs `lilt --version` is a hollow stub. Instead we:
 *   1. run `lilt -h` and assert it exits 0,
 *   2. run `lilt -e "print 1+1"` and assert the stdout starts with "2",
 *      which genuinely exercises the Lil parser/evaluator/print pipeline.
 *
 * Path resolution order:
 *   1. LILT_BIN environment variable (set by test_package/conanfile.py)
 *   2. LILT_DEFAULT_BIN compile-time macro (set by CMakeLists.txt from
 *      Conan's decker_BIN_DIRS / cpp_info.bindirs)
 *   3. /bin/lilt (last-resort fallback)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#ifndef LILT_DEFAULT_BIN
#define LILT_DEFAULT_BIN "/bin/lilt"
#endif

static int exists(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0;
}

int main(void)
{
    const char *env_lilt = getenv("LILT_BIN");
    const char *lilt = (env_lilt && *env_lilt) ? env_lilt : LILT_DEFAULT_BIN;

    if (!exists(lilt)) {
        fprintf(stderr, "lilt binary not found at %s\n", lilt);
        return 1;
    }

    char cmd[1024];
    FILE *pipe;

    /* 1. -h should exit 0 */
    snprintf(cmd, sizeof(cmd), "\"%s\" -h > /dev/null 2>&1", lilt);
    int rc1 = system(cmd);
    if (rc1 != 0) {
        fprintf(stderr, "lilt -h failed (rc=%d)\n", rc1);
        return 2;
    }

    /* 2. evaluate "print [1+1]" — real Lil pipeline, expect stdout "2".
     * Use the array form `print [EXPR]` rather than scalar `print EXPR`:
     * lilt's n_print takes the array branch (print_array → fputc to stdout,
     * unbuffered), which reliably emits the value. The scalar branch goes
     * through fprintf(stdout,...) and lilt exits -e mode without flushing,
     * so scalar print is observably silent. */
    snprintf(cmd, sizeof(cmd), "\"%s\" -e \"print [1+1]\"", lilt);
    pipe = popen(cmd, "r");
    if (!pipe) {
        fprintf(stderr, "popen failed for lilt -e\n");
        return 3;
    }
    char out[256] = "";
    if (fgets(out, sizeof(out), pipe) == NULL) {
        pclose(pipe);
        fprintf(stderr, "lilt -e produced no output\n");
        return 4;
    }
    int rc2 = pclose(pipe);
    if (rc2 != 0) {
        fprintf(stderr, "lilt -e failed (rc=%d)\n", rc2);
        return 5;
    }
    /* strip trailing whitespace from out */
    size_t len = strlen(out);
    while (len > 0 && (out[len-1] == '\n' || out[len-1] == '\r' ||
                       out[len-1] == ' '  || out[len-1] == '\t')) {
        out[--len] = '\0';
    }
    if (strcmp(out, "2") != 0) {
        fprintf(stderr, "lilt -e 'print [1+1]' expected '2', got '%s'\n", out);
        return 6;
    }

    printf("test decker 1.69: OK\n");
    return 0;
}
