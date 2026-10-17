/* test.c — consumer test for uptimed 0.4.6.
 * R34: exercises the packaged bin/uptimed and bin/uprecords binaries.
 * 4 cases: uptimed -v, uprecords -v, uprecords -? usage, invalid option path.
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

/* uptimed -v must print the version banner */
static int test_uptimed_version(void) {
    char buf[8192];
    int rc = read_output("uptimed -v 2>&1", buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "uptimed -v exited non-zero (%d)\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    if (!strstr(buf, "uptimed") || !strstr(buf, "0.4.6")) {
        fprintf(stderr, "version output unexpected\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* uprecords -v must print the version banner */
static int test_uprecords_version(void) {
    char buf[8192];
    int rc = read_output("uprecords -v 2>&1", buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "uprecords -v exited non-zero (%d)\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    if (!strstr(buf, "uprecords") || !strstr(buf, "0.4.6")) {
        fprintf(stderr, "version output unexpected\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* uprecords -? must print the option list */
static int test_uprecords_usage(void) {
    char buf[8192];
    int rc = read_output("uprecords -? 2>&1", buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "uprecords -? exited non-zero (%d)\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    if (!strstr(buf, "usage") && !strstr(buf, "Usage") && !strstr(buf, "-m")) {
        fprintf(stderr, "help output missing usage text\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* invalid option: upstream getopt prints "unrecognized option" + usage and
 * exits 0 on this platform (verified on device) — require a real diagnostic
 * response instead: either a non-zero exit, or usage text in the output.
 * A missing binary (shell 127 "not found") must NOT count as pass. */
static int test_invalid_option(void) {
    char buf[8192];
    int rc = read_output("uptimed -Z 2>&1", buf, sizeof(buf));
    if (buf[0] == '\0') {
        fprintf(stderr, "invalid option produced no diagnostic at all\n");
        return 1;
    }
    if (strstr(buf, "not found") || strstr(buf, "No such file")) {
        fprintf(stderr, "binary missing (harness failure), not app behavior\n---\n%s\n---\n", buf);
        return 1;
    }
    if (rc == 0 && !strstr(buf, "usage") && !strstr(buf, "Usage")) {
        fprintf(stderr, "silent success with no usage diagnostic\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

int main(void) {
    printf("=== uptimed 0.4.6 test_package (OpenHarmony/aarch64) ===\n");
    RUN(test_uptimed_version);
    RUN(test_uprecords_version);
    RUN(test_uprecords_usage);
    RUN(test_invalid_option);
    printf("=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);

    {
        int discovered = 4;
        int passed = tests_run - tests_failed;
        printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"audit upstream (no tests dir, no check_* registration)\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream 0.4.6 ships no tests directory and no Makefile.am registers check_PROGRAMS/TESTS\"}\n");
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_uptimed\",\"discovered\":%d,\"passedCount\":%d}\n",
               (tests_failed == 0) ? "true" : "false", discovered, passed);
    }
    return tests_failed == 0 ? 0 : 1;
}
