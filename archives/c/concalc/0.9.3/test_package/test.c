/* test.c — test_package for concalc 0.9.3 (R34).
 *
 * concalc is a CLI calculator, so the test drives the installed binary and
 * asserts real behaviour:
 *   1. -v prints the version banner "Version: 0.9.3"
 *   2. concalc "2*(3+7/2)" prints 13
 *   3. concalc "1/3" prints 0.333... (34 significant digits, exact string
 *      recorded on the target)
 *   4. concalc "sqrt(2)" prints 1.4142135623730950488016887242097
 *
 * The binary path is passed as argv[1]; the test fails when the package
 * artifacts are removed (CI L1e destructive negative test).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static const char *concalc_bin = NULL;
static int failures = 0;

static void check(int ok, const char *what)
{
    if (ok) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

/* Run the calculator with a single argument; returns exit status, captures
 * (right-trimmed) stdout. */
static int run_expr(const char *arg, char *out, size_t outsz)
{
    char cmd[1024];
    size_t got;
    int status;
    FILE *fp;

    snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\" 2>&1", concalc_bin, arg);
    fp = popen(cmd, "r");
    if (fp == NULL)
        return -1;
    got = fread(out, 1, outsz - 1, fp);
    out[got] = '\0';
    status = pclose(fp);
    if (status == -1)
        return -1;
    while (got > 0 && (out[got - 1] == '\n' || out[got - 1] == '\r' ||
                       out[got - 1] == ' ' || out[got - 1] == '\t'))
        out[--got] = '\0';
    return WEXITSTATUS(status);
}

static void run_version(void)
{
    char cmd[1024];
    char out[512];
    size_t got;
    FILE *fp;

    snprintf(cmd, sizeof(cmd), "\"%s\" -v 2>&1", concalc_bin);
    fp = popen(cmd, "r");
    if (fp == NULL) {
        check(0, "-v prints version banner 0.9.3");
        return;
    }
    got = fread(out, 1, sizeof(out) - 1, fp);
    out[got] = '\0';
    pclose(fp);
    check(strstr(out, "Version: 0.9.3") != NULL, "-v prints version banner 0.9.3");
}

int main(int argc, char *argv[])
{
    char out[512];
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-concalc>\n", argv[0]);
        return 1;
    }
    concalc_bin = argv[1];
    printf("Testing concalc binary: %s\n", concalc_bin);

    run_version();

    rc = run_expr("2*(3+7/2)", out, sizeof(out));
    check(rc == 0 && strcmp(out, "13") == 0, "2*(3+7/2) evaluates to 13");

    rc = run_expr("1/3", out, sizeof(out));
    check(rc == 0 && strncmp(out, "0.333333333333333333333333333333333", 34) == 0,
          "1/3 evaluates to the 34-digit 0.333...");

    rc = run_expr("sqrt(2)", out, sizeof(out));
    check(rc == 0 && strcmp(out, "1.4142135623730950488016887242097") == 0,
          "sqrt(2) evaluates to 1.4142135623730950488016887242097");

    if (failures != 0) {
        printf("%d test(s) failed\n", failures);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
