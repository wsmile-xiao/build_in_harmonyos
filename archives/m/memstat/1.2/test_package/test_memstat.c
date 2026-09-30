/* test_memstat.c — consumer test for memstat 1.2 (OpenHarmony / aarch64).
 *
 * R34: every case executes the packaged bin/memstat binary through a real
 * fork/exec and asserts on its real exit status and real output.  Nothing is
 * printed in place of a check.
 *
 * Cases 3-5 drive the /proc scanner, which is exactly the code path repaired
 * by patches/0001-memstat-c-musl-strtol-errno-and-path-max.patch.  Against the unpatched
 * memstat.c on the OHOS (musl) libc, read_proc() aborts on the first
 * readdir() entry with "strtol: Invalid argument" and exit 1, so these three
 * cases fail before the adaptation and pass after it.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int tests_run = 0;
static int tests_failed = 0;

#define RUN(fn) do { \
    tests_run++; \
    printf("[TEST %d] %s ... ", tests_run, #fn); \
    fflush(stdout); \
    if (fn() == 0) { printf("PASS\n"); } \
    else { printf("FAIL\n"); tests_failed++; } \
} while (0)

/* Runs cmd through the shell, captures up to cap-1 bytes into buf (always
 * NUL-terminated) and drains the pipe so the child can never block on a full
 * pipe.  Returns the pclose() status, or -1 if popen() itself failed. */
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

/* Extracts the pid from memstat's process-summary line and returns how many
 * such lines the report holds.
 *
 * Upstream prints the summary as "%7ldk: PID %5d (%s)" -- the pid is a
 * *space-padded, 5-wide right-aligned* field.  Matching the literal text
 * "PID <pid>" therefore only ever succeeds when the pid happens to be five
 * digits or more; a 1-4 digit pid renders as "PID    12" / "PID   974" and the
 * substring is absent.  That makes such an assertion a coin flip on the
 * runtime's pid width (it fails deterministically under qemu-user emulation
 * and on a freshly booted device, where pids are small).  Parse the field
 * numerically instead -- scanf's %d skips leading blanks -- so the check
 * holds for any pid width.
 *
 * ": PID " is the stable anchor: the literal separator memstat always emits
 * between the kilobyte field and the pid field, independent of padding. */
static int find_process_pid(const char *hay, long *pid_out) {
    const char *p = hay;
    int found = 0;

    while ((p = strstr(p, ": PID ")) != NULL) {
        int pid = 0;
        if (sscanf(p, ": PID %d", &pid) == 1) {
            if (found == 0) *pid_out = (long)pid;
            found++;
        }
        p += 6; /* strlen(": PID ") */
    }
    return found;
}

/* Case 1: `-v` prints the version banner plus the full option list to stderr
 * and exits 1.  Asserting on "usage:" is what proves the packaged binary
 * really ran: a missing/unrunnable binary would surface the shell's own
 * "not found" diagnostic and exit 127, which carries no "usage:" text. */
static int test_usage_banner(void) {
    char buf[8192];
    int rc = read_output("memstat -v 2>&1", buf, sizeof(buf));
    if (rc == 0) {
        fprintf(stderr, "memstat -v must exit non-zero\n---\n%s\n---\n", buf);
        return 1;
    }
    if (!strstr(buf, "usage:") || !strstr(buf, "memstat")) {
        fprintf(stderr, "usage banner missing program name\n---\n%s\n---\n", buf);
        return 1;
    }
    if (!strstr(buf, "[-n] [-v] [-w] [-p pid]")) {
        fprintf(stderr, "usage banner does not list the full option set\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* Case 2: an unrecognised option must be rejected with a diagnostic, and the
 * getopt() failure path must still print the usage banner. */
static int test_invalid_option(void) {
    char buf[8192];
    int rc = read_output("memstat -Z 2>&1", buf, sizeof(buf));
    if (rc == 0) {
        fprintf(stderr, "invalid option must not exit 0\n---\n%s\n---\n", buf);
        return 1;
    }
    if (buf[0] == '\0') {
        fprintf(stderr, "invalid option produced no diagnostic\n");
        return 1;
    }
    if (!strstr(buf, "usage:")) {
        fprintf(stderr, "invalid option did not fall through to the usage banner\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* Case 3: the core functional test.  `memstat -n -p <self>` walks this very
 * process's /proc/<pid>/maps and must succeed, name this process, emit the
 * section separator and close with the grand-total line.  `-n` keeps memstat
 * from trying to open /etc/memstat.conf for inode resolution, which does not
 * exist on a stock OHOS device. */
static int test_snapshot_own_pid(void) {
    char buf[65536];
    char cmd[64];
    long pid = -1;
    int rc;
    int n;
    const char *tail;
    size_t len;

    snprintf(cmd, sizeof(cmd), "memstat -n -p %ld 2>&1", (long)getpid());
    rc = read_output(cmd, buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "memstat -n -p <self> exited %d\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    /* Compare the pid numerically, not as text: memstat pads it to five
     * columns, so "PID 974" is really printed as "PID   974".  See
     * find_process_pid(). */
    n = find_process_pid(buf, &pid);
    if (n < 1) {
        fprintf(stderr, "report has no process-summary line for this process\n---\n%s\n---\n", buf);
        return 1;
    }
    if (pid != (long)getpid()) {
        fprintf(stderr, "report names pid %ld, expected this process %ld\n---\n%s\n---\n",
                pid, (long)getpid(), buf);
        return 1;
    }
    if (!strstr(buf, "--------")) {
        fprintf(stderr, "report is missing the summary separator\n---\n%s\n---\n", buf);
        return 1;
    }
    /* summarize_usage() always ends with "<total>k (<shared>k)".  Trim the
     * trailing newline first, otherwise strrchr() lands on the empty string
     * after the final '\n' instead of on that line. */
    len = strlen(buf);
    while (len > 0 && (buf[len - 1] == '\n' || buf[len - 1] == '\r' || buf[len - 1] == ' ')) {
        buf[--len] = '\0';
    }
    tail = strrchr(buf, '\n');
    if (tail == NULL || strchr(tail, '(') == NULL) {
        fprintf(stderr, "report is missing the grand-total line\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

/* Case 4: `-p` really filters.  Exactly one process-summary line may appear
 * when the scan is restricted to a single pid, and every shared-object line
 * must be attributed to that pid. */
static int test_pid_filter_is_exclusive(void) {
    char buf[65536];
    char cmd[64];
    long pid = -1;
    int rc;
    int n;

    snprintf(cmd, sizeof(cmd), "memstat -n -p %ld 2>&1", (long)getpid());
    rc = read_output(cmd, buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "memstat -n -p <self> exited %d\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    n = find_process_pid(buf, &pid);
    if (n != 1) {
        fprintf(stderr, "expected exactly 1 process line for a single-pid scan, got %d\n---\n%s\n---\n",
                n, buf);
        return 1;
    }
    if (pid != (long)getpid()) {
        fprintf(stderr, "single-pid scan reported pid %ld, expected %ld\n---\n%s\n---\n",
                pid, (long)getpid(), buf);
        return 1;
    }
    return 0;
}

/* Case 5: the negative side of the same filter.  A pid that does not exist
 * yields an empty but well-formed report: separator plus a zeroed grand
 * total, and no process lines at all. */
static int test_unknown_pid_reports_empty(void) {
    char buf[8192];
    long pid = -1;
    int rc;

    rc = read_output("memstat -n -p 999999999 2>&1", buf, sizeof(buf));
    if (rc != 0) {
        fprintf(stderr, "memstat -n -p 999999999 exited %d\n---\n%s\n---\n", rc, buf);
        return 1;
    }
    if (find_process_pid(buf, &pid) != 0) {
        fprintf(stderr, "unknown pid must not produce a process line\n---\n%s\n---\n", buf);
        return 1;
    }
    if (!strstr(buf, "--------") || !strstr(buf, "0k (")) {
        fprintf(stderr, "unknown pid must still emit a zeroed report\n---\n%s\n---\n", buf);
        return 1;
    }
    return 0;
}

int main(void) {
    int passed;

    printf("=== memstat 1.2 test_package (OpenHarmony/aarch64) ===\n");
    RUN(test_usage_banner);
    RUN(test_invalid_option);
    RUN(test_snapshot_own_pid);
    RUN(test_pid_filter_is_exclusive);
    RUN(test_unknown_pid_reports_empty);

    passed = tests_run - tests_failed;
    printf("=== Results: %d/%d passed, %d failed ===\n", passed, tests_run, tests_failed);

    /* Upstream ships no test suite at all: memstat 1.2 is a single memstat.c
     * plus a 4-target Makefile (memstat/clean/install) with no check/test
     * target and no tests/ directory.  Declared as such rather than claimed
     * as upstream coverage -- see test_package/MANIFEST.yml for the audit. */
    printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"audit upstream (no tests dir, no check target)\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream memstat 1.2 ships no tests directory and its Makefile registers only memstat/clean/install targets\"}\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"test_memstat\",\"discovered\":%d,\"passedCount\":%d}\n",
           (tests_failed == 0) ? "true" : "false", tests_run, passed);

    return tests_failed == 0 ? 0 : 1;
}
