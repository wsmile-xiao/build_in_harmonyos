/* test_package/test.c — run the installed fluent-bit binary to verify the package.
 * This is the L1 official test: it MUST depend on the fluent-bit package,
 * otherwise the R34 destructive negative test (L1e) detects a fake test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

/* Reject shell metacharacters in the binary path to avoid command injection
 * when it is interpolated into a `system()` command line. */
static int is_safe_path(const char *s) {
    const char *p;
    if (!s || !*s) {
        return 0;
    }
    for (p = s; *p; p++) {
        if (isalnum((unsigned char)*p) || *p == '/' || *p == '.' ||
            *p == '-' || *p == '_' || *p == '+' || *p == '=' || *p == ':') {
            continue;
        }
        return 0;  /* shell metacharacter or space found */
    }
    return 1;
}

static int build_command(char *cmd, size_t size, const char *bin, const char *arg) {
    int n;

    n = snprintf(cmd, size, "\"%s\" %s", bin, arg);
    if (n < 0 || (size_t)n >= size) {
        printf("[fail] command too long for fluent-bit %s\n", arg);
        return 0;
    }

    return 1;
}

int main(int argc, char **argv) {
    /* Path to the installed fluent-bit binary is passed via the FLUENT_BIT_BIN
     * env var (set by conanfile.py test() — absolute path into the conan
     * package folder). Fall back to PATH lookup only if unset. */
    const char *bin = getenv("FLUENT_BIT_BIN");
    char cmd[512];
    int rc;

    if (!bin || !*bin) {
        bin = "fluent-bit";  /* rely on PATH */
    }

    if (!is_safe_path(bin)) {
        printf("[fail] FLUENT_BIT_BIN contains shell metacharacters: %s\n", bin);
        return 1;
    }

    /* Build a shell command: "<bin>" --version */
    if (!build_command(cmd, sizeof(cmd), bin, "--version")) {
        return 1;
    }

    printf("[test] Running: %s\n", cmd);
    rc = system(cmd);
    if (rc != 0) {
        printf("[fail] fluent-bit --version exited %d\n", rc);
        return 1;
    }
    printf("[ok] fluent-bit --version succeeded (exit 0)\n");

    /* Also check --help exits successfully (fluent-bit returns 0 for --help) */
    if (!build_command(cmd, sizeof(cmd), bin, "--help")) {
        return 1;
    }
    printf("[test] Running: %s\n", cmd);
    rc = system(cmd);
    if (rc != 0) {
        printf("[fail] fluent-bit --help exited %d\n", rc);
        return 1;
    }
    printf("[ok] fluent-bit --help succeeded (exit 0)\n");
    return 0;
}
