/* test_input_utils.c — real consumer test for input-utils 1.3.
 * Runs the packaged ELF tools and asserts exit codes / error output:
 *  1. lsinput empty scan exits 0
 *  2. input-events 9999 reports open failure of /dev/input/event9999
 *  3. emulate-key without keyname: usage rejection (non-zero)
 *  4. input-send without device: usage rejection (non-zero, "usage" text)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
static int checks = 0;

static int run_capture(const char *cmd, char *out, size_t outsz)
{
    FILE *p = popen(cmd, "r");
    size_t n = 0;
    int rc;
    if (!p)
        return -1;
    if (out) {
        while (n + 1 < outsz && fgets(out + n, (int)(outsz - n), p))
            n += strlen(out + n);
    } else {
        char buf[256];
        while (fgets(buf, sizeof(buf), p))
            ;
    }
    rc = pclose(p);
    return rc == -1 ? -1 : rc;
}

static void ok(const char *name)
{
    checks++;
    printf("[ok] %s\n", name);
}

static void bad(const char *name)
{
    checks++;
    failures++;
    printf("[FAIL] %s\n", name);
}

int main(void)
{
    int rc;
    char buf[4096];

    /* 1. lsinput: empty /dev/input scan must exit 0 */
    rc = run_capture("lsinput >/dev/null 2>&1", NULL, 0);
    if (rc == 0)
        ok("lsinput: empty scan exit 0");
    else
        bad("lsinput: expected exit 0");

    /* 2. input-events 9999: upstream main() returns 0 unconditionally, so
     * assert the observable contract: open failure of event9999 on stderr */
    rc = run_capture("input-events 9999 2>&1 >/dev/null", buf, sizeof(buf));
    if (strstr(buf, "/dev/input/event9999"))
        ok("input-events 9999: reported open of /dev/input/event9999");
    else
        bad("input-events 9999: stderr missing /dev/input/event9999");

    /* 3. emulate-key without keyname: usage rejection */
    rc = run_capture("emulate-key >/dev/null 2>&1", NULL, 0);
    if (rc != 0)
        ok("emulate-key: usage rejection non-zero");
    else
        bad("emulate-key: expected non-zero exit");

    /* 4. input-send without device: usage rejection */
    memset(buf, 0, sizeof(buf));
    rc = run_capture("input-send 2>&1 >/dev/null", buf, sizeof(buf));
    if (rc != 0 && strstr(buf, "usage"))
        ok("input-send: usage rejection non-zero");
    else
        bad("input-send: expected non-zero usage exit");

    printf("\ntest_input_utils: %d checks, %d failures\n", checks, failures);
    if (failures > 0) {
        printf("ALL TESTS FAILED\n");
        return 1;
    }
    printf("ALL TESTS PASSED\n");
    return 0;
}
