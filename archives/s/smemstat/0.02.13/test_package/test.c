/* test.c — consumer test for smemstat 0.02.13.
 * R34: exercises the packaged bin/smemstat binary (not a stub).
 * 3 cases: -h usage+version, one-shot memory snapshot, invalid option path.
 * Emits HMBS hard-gate markers with counts from the same counters.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int tests_run = 0;
static int tests_failed = 0;

#define RUN(fn) do { \
    tests_run++; \
    printf("[TEST %d] %s ... ", tests_run, #fn); \
    fflush(stdout); \
    if (fn() == 0) { printf("PASS\n"); } \
    else { printf("FAIL\n"); tests_failed++; } \
} while (0)

/* Runs cmd, captures up to cap-1 bytes into buf (always NUL-terminated,
 * buf[0] = '\0' before use), then drains the pipe so the child can never
 * block on a full pipe. Returns the pclose() status (<0 if popen failed). */
static int read_output(const char *cmd, char *buf, size_t cap) {
    FILE *fp;
    size_t n = 0;
    int c;
    int rc;
    buf[0] = '\0';
    fp = popen(cmd, "r");
    if (!fp) return -1;
    while ((c = fgetc(fp)) != EOF) {
        if (n + 1 < cap) buf[n++] = (char)c;
    }
    buf[n] = '\0';
    rc = pclose(fp);
    return rc;
}

/* -h must print the usage banner including the version string */
static int test_help(void) {
    char buf[8192];
    int rc = read_output("smemstat -h 2>&1", buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "smemstat -h exited non-zero (%d)\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    if (!strstr(buf, "Usage") || !strstr(buf, "0.02.13")) {
        fprintf(stderr, "help output missing usage/version text\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* one-shot snapshot: `smemstat -k 1 1` samples /proc memory once and exits */
static int test_snapshot(void) {
    char buf[16384];
    int rc = read_output("smemstat -k 1 1 2>&1", buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "smemstat -k 1 1 exited non-zero (%d)\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    if (strlen(buf) < 64) {
        fprintf(stderr, "snapshot output suspiciously small\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* invalid option must fail AND print a diagnostic (getopt returns '?' ->
 * show_usage + exit failure; a missing binary would exit 127 with a shell
 * diagnostic — both carry text, so require non-zero rc plus non-empty
 * output, never a silent success) */
static int test_invalid_option(void) {
    char buf[8192];
    int rc = read_output("smemstat -Z 2>&1", buf, sizeof(buf));
    if (rc == 0) {
        fprintf(stderr, "invalid option must not exit 0\n---\n%s\n---\n", buf);
        return 1;
    }
    if (buf[0] == '\0') {
        fprintf(stderr, "invalid option produced no diagnostic\n");
        return 1;
    }
    return 0;
}

int main(void) {
    printf("=== smemstat 0.02.13 test_package (OpenHarmony/aarch64) ===\n");
    RUN(test_help);
    RUN(test_snapshot);
    RUN(test_invalid_option);
    printf("=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);

    {
        int discovered = 3;
        int passed = tests_run - tests_failed;
        printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"audit upstream (no tests dir, no check target)\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream 0.02.13 ships no tests directory and the Makefile registers no check/test target\"}\n");
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_smemstat\",\"discovered\":%d,\"passedCount\":%d}\n",
               (tests_failed == 0) ? "true" : "false", discovered, passed);
    }
    return tests_failed == 0 ? 0 : 1;
}
