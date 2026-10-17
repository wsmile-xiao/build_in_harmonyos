/* test_decode.c — rtl-wmbus 1.1.0 consumer functional test.
 *
 * Drives the *packaged* rtl_wmbus executable: forks it, feeds it a recorded
 * RTL-SDR cu8 capture on stdin and inspects the decoded WM-Bus telegrams it
 * writes to stdout. Every assertion is made against real decoder output — the
 * capture is a real 868.625 MHz RF recording shipped by upstream, and the
 * expected payload was taken from upstream's own documented invocation
 * (`cat samples/rtlsdr_868.625M_2M4_issue48.cu8 | rtl_wmbus -d 3 -s -o`).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef FIXTURE_CU8
#error "FIXTURE_CU8 must be provided by CMake (-DFIXTURE_CU8=...)"
#endif

/* Package bin/ is on PATH via VirtualRunEnv; allow an explicit override. */
static const char *rtl_bin(void)
{
    const char *e = getenv("RTL_WMBUS_BIN");
    return (e && *e) ? e : "rtl_wmbus";
}

/* Upstream telegram recovered from this fixture (868.625 MHz, T1 mode).
 * Format: MODE;CRC_OK;MODE_OK;TIMESTAMP;RSSI;...;ADDRESS;PAYLOAD */
#define EXP_ADDR   "60168569"
#define EXP_PAYLOAD "0x294468506985166076f0a0009f2f613000186130008061000109006ba1007cb2008dc3009ed4000fe500"
#define EXP_FRAMES 2

static int failures;
static int checks;

static void ok(int cond, const char *fmt, ...)
{
    va_list ap;
    checks++;
    va_start(ap, fmt);
    if (cond) {
        printf("  [ok]   ");
    } else {
        printf("  [FAIL] ");
        failures++;
    }
    vprintf(fmt, ap);
    printf("\n");
    va_end(ap);
    fflush(stdout);
}

/* Run rtl_wmbus with argv, optionally feeding `infile` on stdin, capturing
 * stdout. Returns the child exit status, or -1 if it could not be run.
 *
 * Deadlock note: the child consumes all of stdin before emitting anything, and
 * its entire stdout is ~200 bytes, far below the 64 KiB pipe buffer. The
 * sequential write-then-read below is therefore safe. */
static int run_rtl(char *const argv[], const char *infile, char *out, size_t outcap)
{
    int pin[2] = {-1, -1}, pout[2] = {-1, -1};
    size_t used = 0;
    int status = 0;

    if (outcap)
        out[0] = '\0';
    if (pipe(pin) != 0 || pipe(pout) != 0)
        return -1;

    pid_t pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        dup2(pin[0], STDIN_FILENO);
        dup2(pout[1], STDOUT_FILENO);
        close(pin[0]);
        close(pin[1]);
        close(pout[0]);
        close(pout[1]);
        execvp(rtl_bin(), argv);
        _exit(127);
    }

    close(pin[0]);
    close(pout[1]);

    if (infile) {
        int fd = open(infile, O_RDONLY);
        if (fd < 0) {
            close(pin[1]);
            close(pout[0]);
            waitpid(pid, &status, 0);
            return -2;                      /* fixture missing */
        }
        char buf[65536];
        ssize_t n;
        while ((n = read(fd, buf, sizeof buf)) > 0) {
            ssize_t off = 0;
            while (off < n) {
                ssize_t w = write(pin[1], buf + off, (size_t)(n - off));
                if (w <= 0) {
                    if (errno == EINTR)
                        continue;
                    break;
                }
                off += w;
            }
        }
        close(fd);
    }
    close(pin[1]);                          /* EOF -> decoder flushes */

    for (;;) {
        if (outcap && used + 1 < outcap) {
            ssize_t n = read(pout[0], out + used, outcap - used - 1);
            if (n > 0)
                used += (size_t)n;
            else if (n == 0)
                break;
            else if (errno != EINTR)
                break;
        } else {
            char drain[4096];
            if (read(pout[0], drain, sizeof drain) <= 0)
                break;
        }
    }
    close(pout[0]);

    /* NUL-terminate: without this the tail of a previous, longer run would be
     * counted by the caller's line/payload checks. */
    if (outcap && used < outcap)
        out[used] = '\0';

    while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
        ;
    if (WIFEXITED(status))
        return WEXITSTATUS(status);
    return -1;
}

static int count_lines(const char *s)
{
    int n = 0;
    for (; *s; s++)
        if (*s == '\n')
            n++;
    return n;
}

/* Split "a;b;c;..." in place; returns field count, fills up to max fields. */
static int split_fields(char *line, char **fields, int max)
{
    int n = 0;
    char *p = line;
    while (n < max) {
        fields[n++] = p;
        char *semi = strchr(p, ';');
        if (!semi)
            break;
        *semi = '\0';
        p = semi + 1;
    }
    return n;
}

int main(void)
{
    char out[65536];
    char *f[16];
    int rc, nf, frames;

    printf("rtl-wmbus consumer functional test (fixture: %s)\n", FIXTURE_CU8);

    /* ── 1. version banner ───────────────────────────────────────── */
    {
        char *argv[] = { (char *)rtl_bin(), (char *)"-V", NULL };
        rc = run_rtl(argv, NULL, out, sizeof out);
        ok(rc == 0, "`rtl_wmbus -V` exits 0 (got %d)", rc);
        ok(strstr(out, "rtl_wmbus: 1.1.0") != NULL,
           "-V banner reports the conan version 1.1.0");
        ok(strstr(out, "34684e655df70867ac86e799561ec6512c45be0a") != NULL,
           "-V banner reports the 1.1.0 tag commit hash");
    }

    /* ── 2. usage text ───────────────────────────────────────────── */
    {
        char *argv[] = { (char *)rtl_bin(), (char *)"-p", (char *)"X", NULL };
        rc = run_rtl(argv, NULL, out, sizeof out);
        ok(rc == 1, "invalid mode argument `-p X` exits 1 (got %d)", rc);
        ok(strstr(out, "Usage ") != NULL, "invalid mode argument prints usage");
        ok(strstr(out, "-d 2 set decimation rate to 2") != NULL,
           "usage text documents the -d decimation option");
    }

    /* ── 3. upstream's documented decode invocation ───────────────── */
    {
        char *argv[] = { (char *)rtl_bin(), (char *)"-d", (char *)"3",
                         (char *)"-s", (char *)"-o", NULL };
        rc = run_rtl(argv, FIXTURE_CU8, out, sizeof out);
        ok(rc == 0, "`rtl_wmbus -d 3 -s -o` exits 0 (got %d)", rc);
        ok(rc != -2, "IQ fixture is readable");

        frames = count_lines(out);
        ok(frames == EXP_FRAMES,
           "decoded %d telegram line(s), expected %d", frames, EXP_FRAMES);

        /* Re-walk line by line for the field-level assertions. */
        {
            char *cur = out;
            int addr_ok = 1, mode_ok = 1, payload_ok = 1, rssi_ok = 1;
            while (cur && *cur) {
                char *nl = strchr(cur, '\n');
                if (nl)
                    *nl = '\0';
                if (*cur) {
                    nf = split_fields(cur, f, 16);
                    /* MODE;CRC_OK;MODE_OK;TS;RSSI;RSSI;ADDR;PAYLOAD */
                    if (nf < 8 || strcmp(f[0], "T1") != 0 ||
                        strcmp(f[1], "1") != 0 || strcmp(f[2], "1") != 0)
                        mode_ok = 0;
                    if (nf < 8 || strcmp(f[6], EXP_ADDR) != 0)
                        addr_ok = 0;
                    if (nf < 8 || strncmp(f[7], "0x", 2) != 0 ||
                        strcmp(f[7], EXP_PAYLOAD) != 0)
                        payload_ok = 0;
                    if (nf >= 6) {
                        char *e1 = NULL, *e2 = NULL;
                        long r1 = strtol(f[4], &e1, 10);
                        long r2 = strtol(f[5], &e2, 10);
                        if (!e1 || *e1 || !e2 || *e2 || r1 <= 0 || r2 <= 0)
                            rssi_ok = 0;
                    } else {
                        rssi_ok = 0;
                    }
                }
                cur = nl ? nl + 1 : NULL;
            }
            ok(mode_ok, "every line is a CRC-checked T1 telegram (T1;1;1)");
            ok(addr_ok, "every telegram reports meter address %s", EXP_ADDR);
            ok(payload_ok, "every telegram payload matches the upstream decode");
            ok(rssi_ok, "every telegram reports positive RSSI levels");
        }
    }

    /* ── 4. mode filtering is honoured ────────────────────────────── */
    {
        char *argv_t[] = { (char *)rtl_bin(), (char *)"-d", (char *)"3",
                           (char *)"-s", (char *)"-o", (char *)"-p",
                           (char *)"T", NULL };
        rc = run_rtl(argv_t, FIXTURE_CU8, out, sizeof out);
        ok(rc == 0, "`-p T` (T1/C1 processing disabled) exits 0 (got %d)", rc);
        ok(count_lines(out) == 0,
           "-p T suppresses all T1 telegrams (got %d)", count_lines(out));
    }
    {
        char *argv_s[] = { (char *)rtl_bin(), (char *)"-d", (char *)"3",
                           (char *)"-s", (char *)"-o", (char *)"-p",
                           (char *)"S", NULL };
        rc = run_rtl(argv_s, FIXTURE_CU8, out, sizeof out);
        ok(rc == 0, "`-p S` (S1 processing disabled) exits 0 (got %d)", rc);
        ok(count_lines(out) == EXP_FRAMES,
           "-p S keeps the T1 telegrams intact (got %d)", count_lines(out));
    }

    /* ── 5. graceful behaviour on a truncated capture ─────────────── */
    {
        char *argv[] = { (char *)rtl_bin(), (char *)"-d", (char *)"3",
                         (char *)"-s", (char *)"-o", NULL };
        rc = run_rtl(argv, "/dev/null", out, sizeof out);
        ok(rc == 0, "empty stdin is handled gracefully (exit %d)", rc);
        ok(count_lines(out) == 0, "empty stdin yields no telegrams");
    }

    (void)nf;
    printf("\n%d checks, %d failure(s)\n", checks, failures);
    return failures ? 1 : 0;
}
