/*
 * ohos_procfs_probe.c — HarmonyOS-specific consumer test for wmload 0.9.7.
 *
 * WHY THIS PROBE EXISTS
 * ---------------------
 * wmload's only platform-specific runtime dependency is the procfs CPU-time
 * contract.  Everything else it does is X11 window handling, which no headless
 * build host can execute (see test_wmload.sh, where the GUI-only cases are
 * declared per-case SKIP with their observed signatures).  The contract the
 * dockapp's graph is made of is:
 *
 *   wmload.c:522  fd = open("/proc/stat", O_RDONLY);
 *   wmload.c:527  p = skip_token(buffer);              // consumes "cpu"
 *                 cp_time[0..3] = strtoul(p, &p, 0);   // user nice system idle
 *   wmload.c:515  GetLoad() rounds Maximum * delta / total for the four bars
 *
 * This probe consumes that contract on HarmonyOS PC aarch64 in three layers,
 * and every layer reports its own machine-readable verdict rather than
 * collapsing into one green tick:
 *
 *   L1 ABI      — the widths GetLoad()'s arithmetic rests on (LP64,
 *                 8-byte unsigned long, matching cp_time[]).
 *   L2 PARSE    — the upstream skip_token()/strtoul(...,0) sequence and the
 *                 delta/percentage arithmetic, driven over synthetic
 *                 /proc/stat-shaped fixtures.  Deterministic: it does not
 *                 depend on how busy the machine is, so it asserts the
 *                 algorithm itself instead of sampling luck.  It also asserts
 *                 that a truncated record is REJECTED, so a broken read can
 *                 never be mistaken for a valid zero sample.
 *   L3 LIVE     — the real /proc.  /proc/meminfo is read as a control that
 *                 proves /proc itself is reachable from this process; then the
 *                 literal path wmload opens is read and, when readable, the
 *                 two-sample delta model is asserted for real.
 *
 * The live /proc/stat step is SKIPPED WITH ITS OBSERVED ERRNO, never reported
 * as a pass, when the platform denies it.  On HarmonyOS PC the SELinux label
 * u:object_r:proc_stat_file:s0 denies /proc/stat to unprivileged processes —
 * the same limitation this repository already recorded for htop 3.4.1
 * ("/proc/stat 需 sudo（平台限制）", archives/h/htop/3.4.1/notes.md).  A probe
 * that silently reported PASS there would be lying about a resource it never
 * opened.
 *
 * A note on buffer size: upstream reads into a 100-byte stack buffer, which
 * only survives because /proc/stat's first line is short.  The probe reads up
 * to 4096 bytes so that a machine with many cpuN lines cannot split the
 * aggregate line; the *parse* is the upstream one, the read size is not part
 * of the contract.
 *
 * Output is TAP-like ("ok N - label" / "not ok N - label" / "ok N - label
 * # SKIP reason"), followed by a summary line the caller greps for:
 *   WMLOAD_OHOS_PROCFS probes=<total> passed=<n> skipped=<n> failures=<n>
 */

#define _POSIX_C_SOURCE 200112L

#include <stdio.h>
#include <stdlib.h>

#ifdef __OHOS__

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define STAT_PATH "/proc/stat"
#define CONTROL_PATH "/proc/meminfo"
#define COUNTER_COUNT 4
#define LINE_BUFFER 512
#define READ_BUFFER 4096
#define LIVE_ATTEMPTS 5

static int assertions;
static int passed;
static int skipped;
static int failures;

static void check(int condition, const char *label)
{
    ++assertions;
    if (condition) {
        ++passed;
        printf("ok %d - %s\n", assertions, label);
    } else {
        ++failures;
        printf("not ok %d - %s\n", assertions, label);
    }
    fflush(stdout);
}

/* Never counted as a pass: an unexercised case is declared, with its reason. */
static void skip(const char *label, const char *reason)
{
    ++assertions;
    ++skipped;
    printf("ok %d - %s # SKIP %s\n", assertions, label, reason);
    fflush(stdout);
}

/* Upstream wmload.c:508 skip_token(), same contract. */
static const char *skip_token(const char *p)
{
    while (isspace((unsigned char)*p)) {
        p++;
    }
    while (*p && !isspace((unsigned char)*p)) {
        p++;
    }
    return p;
}

/* Count whitespace-separated fields of a line, label included. */
static size_t count_fields(const char *line)
{
    size_t fields = 0;
    int inside = 0;

    for (; *line; line++) {
        if (isspace((unsigned char)*line)) {
            inside = 0;
        } else if (!inside) {
            inside = 1;
            fields++;
        }
    }
    return fields;
}

/*
 * Mirrors GetLoad() (wmload.c:515-554): skip the record's label and parse
 * COUNTER_COUNT cumulative counters as unsigned long with base 0, exactly as
 * upstream does.  Returns 0 on success and -2 on a parse error, so a caller
 * cannot mistake a failed parse for a legitimate zero.
 */
static int parse_counters(const char *buffer, unsigned long counters[COUNTER_COUNT])
{
    const char *cursor = skip_token(buffer);
    size_t parsed;

    for (parsed = 0; parsed < COUNTER_COUNT; parsed++) {
        char *end = NULL;
        errno = 0;
        counters[parsed] = strtoul(cursor, &end, 0);
        if (end == cursor || errno != 0) {
            return -2;
        }
        cursor = end;
    }
    return 0;
}

/* The aggregate record is "cpu ", never a per-cpu "cpuN" record. */
static int is_aggregate_line(const char *line)
{
    return strncmp(line, "cpu ", 4) == 0;
}

/*
 * Round-half-up percentage: the integer form of GetLoad()'s rint() split of
 * Maximum * delta / total.
 */
static unsigned long percent(unsigned long part, unsigned long total)
{
    if (total == 0) {
        return 0;
    }
    return (100UL * part + total / 2UL) / total;
}

/*
 * Read the first newline-terminated record of a path.  Returns 0 on success,
 * -1 on failure with errno left set by the failing call (open or read), so the
 * caller can report the platform's actual error rather than a guess.
 */
static int read_first_record(const char *path, char *line, size_t line_size)
{
    char buffer[READ_BUFFER];
    ssize_t length;
    int fd;
    const char *newline;
    size_t record;

    if (line_size == 0) {
        errno = EINVAL;
        return -1;
    }
    fd = open(path, O_RDONLY);
    if (fd < 0) {
        return -1;
    }
    length = read(fd, buffer, sizeof(buffer) - 1);
    (void)close(fd);
    if (length <= 0) {
        if (length == 0) {
            errno = EIO;
        }
        return -1;
    }
    buffer[length] = '\0';

    newline = strchr(buffer, '\n');
    record = newline ? (size_t)(newline - buffer) : (size_t)length;
    if (record >= line_size) {
        record = line_size - 1;
    }
    memcpy(line, buffer, record);
    line[record] = '\0';
    return 0;
}

/* --- L2 fixtures: two consecutive snapshots of one machine ------------- */

static const char FIXTURE_FIRST[] =
    "cpu  1000 100 2000 3000 50 20 0 0 0 0\n"
    "cpu0 500 50 1000 1500 25 10 0 0 0 0\n"
    "cpu1 500 50 1000 1500 25 10 0 0 0 0\n"
    "intr 4242 0 0\n"
    "ctxt 99999\n";

static const char FIXTURE_SECOND[] =
    "cpu  1100 100 2300 3500 60 20 0 0 0 0\n"
    "cpu0 550 50 1150 1750 30 10 0 0 0 0\n"
    "cpu1 550 50 1150 1750 30 10 0 0 0 0\n"
    "intr 4243 0 0\n"
    "ctxt 100120\n";

/* Only three of the four counters are present: the parse must refuse it. */
static const char FIXTURE_TRUNCATED[] = "cpu  1000 100 2000\n";

int main(void)
{
    char first_line[LINE_BUFFER];
    unsigned long first[COUNTER_COUNT];
    unsigned long second[COUNTER_COUNT];
    unsigned long delta[COUNTER_COUNT];
    unsigned long first_total = 0;
    unsigned long second_total = 0;
    unsigned long delta_total;
    int last_read_ok;
    int advanced;
    int attempt;
    unsigned long sum_percent = 0;
    struct timespec pause;
    size_t index;
    int status;

    memset(first_line, 0, sizeof(first_line));

    /* --- L1 ABI layer ---------------------------------------------------- */
    check(sizeof(void *) == 8, "HarmonyOS PC aarch64 is LP64 (pointer width 8)");
    check(sizeof(unsigned long) == 8,
          "strtoul container is 64-bit, as in upstream cp_time[]");

    /* --- L2 parse-contract layer, over deterministic fixtures ------------ */
    status = parse_counters(FIXTURE_FIRST, first);
    check(status == 0, "fixture: upstream skip_token()+strtoul(x4) parses the aggregate record");
    check(status == 0 && first[0] == 1000 && first[1] == 100 && first[2] == 2000 && first[3] == 3000,
          "fixture: the four counters land in user/nice/system/idle order (wmload.c:527)");
    check(is_aggregate_line(FIXTURE_FIRST),
          "fixture: aggregate \"cpu \" record is distinguished from a per-cpu \"cpuN\" record");
    check(!is_aggregate_line(FIXTURE_FIRST + strlen("cpu  1000 100 2000 3000 50 20 0 0 0 0\n")),
          "fixture: a cpuN record is NOT accepted as the aggregate record");
    check(count_fields(FIXTURE_FIRST) >= COUNTER_COUNT + 1,
          "fixture: aggregate record carries the 4 counters GetLoad() consumes (plus label)");
    check(parse_counters(FIXTURE_TRUNCATED, second) == -2,
          "fixture: a truncated record is rejected, not read as a valid zero sample");

    for (index = 0; index < COUNTER_COUNT; index++) {
        first_total += first[index];
    }
    check(first_total > 0, "fixture: first snapshot total is non-zero (GetLoad divides by it)");

    check(parse_counters(FIXTURE_SECOND, second) == 0,
          "fixture: second snapshot parses with the same sequence");
    for (index = 0; index < COUNTER_COUNT; index++) {
        second_total += second[index];
    }
    check(second_total >= first_total,
          "fixture: cumulative counters never regress between samples (wmload.c:537-540 model)");

    delta_total = second_total - first_total;
    check(delta_total == 900, "fixture: delta total is the exact sum of the four counter deltas");
    for (index = 0; index < COUNTER_COUNT; index++) {
        delta[index] = second[index] - first[index];
        sum_percent += percent(delta[index], delta_total);
    }
    check(sum_percent >= 99 && sum_percent <= 101,
          "fixture: rint()-style percentage split of the delta partitions 100% (GetLoad rounding)");

    /* --- L3 live procfs layer ------------------------------------------- */
    /*
     * Control first: if /proc/meminfo is readable, the process reaches procfs
     * and a denial on /proc/stat is a label-specific policy decision rather
     * than a broken sandbox.  That distinction is what makes the SKIP below
     * evidence rather than an excuse.
     */
    status = read_first_record(CONTROL_PATH, first_line, sizeof(first_line));
    check(status == 0,
          "control: " CONTROL_PATH " is readable from this process (procfs is reachable)");

    status = read_first_record(STAT_PATH, first_line, sizeof(first_line));
    if (status != 0) {
        char reason[192];
        int saved = errno;
        snprintf(reason, sizeof(reason),
                 "open(\"%s\") failed: errno=%d (%s); on HarmonyOS PC the SELinux label "
                 "u:object_r:proc_stat_file:s0 denies this file to unprivileged processes "
                 "(same platform limit as htop 3.4.1)",
                 STAT_PATH, saved, strerror(saved));
        skip("live: " STAT_PATH " is readable and parses", reason);
        skip("live: two samples 100 ms apart show the counters advancing", reason);
    } else {
        check(is_aggregate_line(first_line),
              "live: first record of " STAT_PATH " is the aggregate \"cpu\" record");
        check(count_fields(first_line) >= COUNTER_COUNT + 1,
              "live: aggregate record carries the 4 counters GetLoad() consumes");
        check(parse_counters(first_line, first) == 0,
              "live: aggregate record parses with the upstream sequence");

        /*
         * The L2 fixture layer already advanced the shared accumulators; the
         * live layer must start from zero or the fixture totals poison every
         * comparison below.  That is exactly the defect the first CI run
         * exposed: first_total still carried the fixture's 6100 ticks while
         * second_total restarted from zero, so both live checks compared a
         * real (few-tick) kernel delta against a fixture-sized head start.
         */
        first_total = 0;
        for (index = 0; index < COUNTER_COUNT; index++) {
            first_total += first[index];
        }
        check(first_total > 0, "live: aggregate total is non-zero");

        pause.tv_sec = 0;
        pause.tv_nsec = 100000000L; /* 100 ms, the nanosleep() idiom of wmload.c:375 */

        /*
         * Cumulative CPU counters advance in whole ticks (USER_HZ), so one
         * 100 ms window is normally worth >= 10 ticks, but a loaded CI
         * worker can postpone the first published sample past the window.
         * Sample up to LIVE_ATTEMPTS windows and accept the first one that
         * advanced; the contract checks below always run on the final sample.
         */
        last_read_ok = 0;
        advanced = 0;
        for (attempt = 0; attempt < LIVE_ATTEMPTS; attempt++) {
            (void)nanosleep(&pause, NULL);
            if (read_first_record(STAT_PATH, first_line, sizeof(first_line)) != 0
                || parse_counters(first_line, second) != 0) {
                last_read_ok = 0;
                continue;
            }
            last_read_ok = 1;
            second_total = 0;
            for (index = 0; index < COUNTER_COUNT; index++) {
                second_total += second[index];
            }
            if (second_total > first_total) {
                advanced = 1;
                break;
            }
        }

        check(last_read_ok && second_total >= first_total,
              "live: cumulative counters never regress between samples");
        check(advanced,
              "live: the kernel advanced the counters: the dockapp graph would move here");
    }

    printf("WMLOAD_OHOS_PROCFS probes=%d passed=%d skipped=%d failures=%d\n",
           assertions, passed, skipped, failures);
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}

#else  /* !__OHOS__ */

/*
 * The probe is HarmonyOS-scoped by design: on any other platform it reports a
 * skip instead of silently passing, so a mis-targeted build cannot be
 * mistaken for platform coverage.
 */
int main(void)
{
    printf("ok 1 - wmload procfs probe is HarmonyOS-specific # SKIP __OHOS__ undefined\n");
    printf("WMLOAD_OHOS_PROCFS probes=1 passed=0 skipped=1 failures=0\n");
    return EXIT_SUCCESS;
}

#endif /* __OHOS__ */
