/* test_dhcp_helper.c — drive the installed dhcp-helper binary through its
 * privilege-free argument paths and assert real behaviour (R34).
 *
 * The relay itself needs root (UDP port 67/1067), which a consumer test
 * environment does not provide; the argument-handling paths below are the
 * upstream code paths reachable unprivileged, each ending in a real
 * exit-code + stderr-message assertion:
 *
 *   1. -v             -> exit 0, "dhcp-helper version 1.2"
 *   2. no arguments   -> exit 1, "no destination specifed"
 *   3. -i <bogus>     -> exit 1, "bad interface"
 *   4. -Z (unknown)   -> exit 1, "Usage: dhcp-helper"
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

struct result {
    int exit_code;
    char output[4096];
};

static int failures = 0;

static struct result run_helper(const char *bin, const char *args) {
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
        fprintf(stderr, "usage: %s <dhcp-helper-binary>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];

    /* 1. -v: version banner on stderr, clean exit. */
    struct result r = run_helper(bin, "-v");
    check(r.exit_code == 0, "dhcp-helper -v exits 0");
    check(strstr(r.output, "dhcp-helper version 1.2") != NULL,
          "dhcp-helper -v reports version 1.2");

    /* 2. missing destination: guarded before any socket binding. */
    r = run_helper(bin, "");
    check(r.exit_code == 1, "dhcp-helper without -s/-b exits 1");
    check(strstr(r.output, "no destination") != NULL,
          "dhcp-helper without -s/-b explains the missing server");

    /* 3. interface validation via SIOCGIFFLAGS. */
    r = run_helper(bin, "-i nosuchif9");
    check(r.exit_code == 1, "dhcp-helper -i <bogus> exits 1");
    check(strstr(r.output, "bad interface") != NULL,
          "dhcp-helper -i <bogus> reports the bad interface");

    /* 4. unknown option: getopt default prints the usage banner. */
    r = run_helper(bin, "-Z");
    check(r.exit_code == 1, "dhcp-helper -Z exits 1");
    check(strstr(r.output, "Usage: dhcp-helper") != NULL,
          "dhcp-helper -Z prints the usage banner");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("all dhcp-helper behaviour checks passed\n");
    return 0;
}
