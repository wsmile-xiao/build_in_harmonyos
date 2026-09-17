/*
 * test_lakai.c — self-authored upstream-level test suite for lakai 0.1 (liblakai)
 *
 * Upstream lakai 0.1 ships NO test suite (see test_package/MANIFEST.yml and
 * notes.md for the inventory evidence).  This file adds an upstream-level test
 * suite so that liblakai's contract is actually exercised.
 *
 * Coverage:
 *   1. lakai_asciitoakai()  — '0'-'9' / 'A'-'Z' / 'a'-'z' / '#' / '+' / '-' / '.'
 *                             boundary mapping + non-convertible chars -> '+'(38)
 *   2. lakai_akaitoascii()  — reverse mapping boundary (incl. gaps -> ' ')
 *   3. ASCII->Akai->ASCII round-trip consistency (40 round-trippable chars)
 *      plus documented lowercase-folding behaviour
 *   4. len semantics: len==0 leaves buffers untouched; partial length converts
 *      only the first `len` bytes
 *   5. lakai_init() / lakai_open() / lakai_close() contract (offline parts)
 *   6. CLI executability of lakbak / lakres / lakclear:
 *        - no args  -> prints "Usage:" and exits non-zero
 *        - bad device -> no crash, prints "Open failed." and exits 5
 *
 * Build (inside conanfile.py build()):
 *   <clang> -I<source_folder> tests/test_lakai.c -L<source_folder> -llakai -o test_lakai
 * Run:
 *   ./test_lakai <source_folder>      # <source_folder> holds the built CLIs
 *
 * The program prints "assertions=N failures=M" and exits non-zero on any failure.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <lakai.h>

static int g_assertions = 0;
static int g_failures = 0;

static void check(int cond, const char *what)
{
    g_assertions++;
    if (cond)
    {
        printf("PASS: %s\n", what);
    }
    else
    {
        g_failures++;
        printf("FAIL: %s\n", what);
        fflush(stdout);
        fprintf(stderr, "FAIL: %s\n", what);
    }
}

/* ── helper: run a program without a shell, capturing stdout+stderr ── */
static int run_capture(char *const argv[], char *out, size_t outsz, int *status_out)
{
    int pipefd[2];
    pid_t pid;
    ssize_t n;
    size_t used = 0;
    int status = 0;

    if (outsz > 0)
        out[0] = '\0';

    if (pipe(pipefd) != 0)
        return -1;

    pid = fork();
    if (pid < 0)
    {
        close(pipefd[0]);
        close(pipefd[1]);
        return -1;
    }

    if (pid == 0)
    {
        /* child: wire stdout+stderr to the pipe and exec directly (no /bin/sh) */
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[0]);
        close(pipefd[1]);
        execv(argv[0], argv);
        _exit(127);
    }

    close(pipefd[1]);
    while ((n = read(pipefd[0], out + used, outsz - 1 - used)) > 0)
    {
        used += (size_t)n;
        if (used >= outsz - 1)
            break;
    }
    out[used] = '\0';
    close(pipefd[0]);

    if (waitpid(pid, &status, 0) < 0)
        return -1;
    if (status_out)
    {
        if (WIFEXITED(status))
            *status_out = WEXITSTATUS(status);
        else if (WIFSIGNALED(status))
            *status_out = 128 + WTERMSIG(status);
        else
            *status_out = -1;
    }
    return 0;
}

/* ── Section A: lakai_asciitoakai boundary mapping ── */
static void test_ascii_to_akai(void)
{
    static const struct { char in; unsigned char out; } cases[] = {
        /* digits */
        { '0', 0 }, { '5', 5 }, { '9', 9 },
        /* uppercase */
        { 'A', 11 }, { 'M', 23 }, { 'Z', 36 },
        /* lowercase folds onto the same Akai codes as uppercase */
        { 'a', 11 }, { 'm', 23 }, { 'z', 36 },
        /* the four punctuation singletons */
        { '#', 37 }, { '+', 38 }, { '-', 39 }, { '.', 40 },
        /* non-convertible ASCII chars fall back to '+' (38) */
        { ' ', 38 }, { '!', 38 }, { '@', 38 }, { '/', 38 }, { '\t', 38 },
    };
    size_t i;
    char label[64];

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++)
    {
        char src[2];
        unsigned char dst = 0xEE;
        src[0] = cases[i].in;
        src[1] = '\0';
        lakai_asciitoakai(src, (char *)&dst, 1);
        snprintf(label, sizeof(label),
                 "lakai_asciitoakai('%c' == %d) -> %u", cases[i].in,
                 (int)(unsigned char)cases[i].in, dst);
        check(dst == cases[i].out, label);
    }
}

/* ── Section B: lakai_akaitoascii boundary mapping ── */
static void test_akai_to_ascii(void)
{
    static const struct { unsigned char in; char out; } cases[] = {
        { 0, '0' }, { 5, '5' }, { 9, '9' },
        /* gap: 10 is not a valid Akai code -> space */
        { 10, ' ' },
        { 11, 'A' }, { 23, 'M' }, { 36, 'Z' },
        { 37, '#' }, { 38, '+' }, { 39, '-' }, { 40, '.' },
        /* other non-convertible codes -> space */
        { 41, ' ' }, { 255, ' ' },
    };
    size_t i;
    char label[64];

    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++)
    {
        char src[1];
        char dst[1];
        src[0] = (char)cases[i].in;
        dst[0] = 0;
        lakai_akaitoascii(src, dst, 1);
        snprintf(label, sizeof(label),
                 "lakai_akaitoascii(%u) -> '%c'", cases[i].in, dst[0]);
        check(dst[0] == cases[i].out, label);
    }
}

/* ── Section C/D: round-trip consistency ── */
static void test_round_trip(void)
{
    /* Round-trippable set: ascii->akai->ascii is the identity here. */
    static const char roundtrip[] =
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ#+-.";
    /* Lowercase folds to uppercase through the Akai encoding. */
    static const char lower[] = "abcdefghijklmnopqrstuvwxyz";
    static const char upper[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    size_t n = sizeof(roundtrip) - 1;
    char *akai = (char *)malloc(n);
    char *back = (char *)malloc(n);
    int i;
    int ok;

    if (akai == NULL || back == NULL)
    {
        check(0, "malloc for round-trip buffers");
        free(akai);
        free(back);
        return;
    }

    lakai_asciitoakai((char *)roundtrip, akai, (int)n);
    lakai_akaitoascii(akai, back, (int)n);
    for (i = 0; i < (int)n; i++)
    {
        char label[80];
        snprintf(label, sizeof(label),
                 "round-trip char #%d '%c' -> '%c'", i, roundtrip[i], back[i]);
        check(back[i] == roundtrip[i], label);
    }

    /* lowercase -> akai -> uppercase (documented fold) */
    ok = 1;
    lakai_asciitoakai((char *)lower, akai, 26);
    lakai_akaitoascii(akai, back, 26);
    if (memcmp(back, upper, 26) != 0)
        ok = 0;
    check(ok, "lowercase 'a'-'z' folds to 'A'-'Z' through Akai encoding");

    free(akai);
    free(back);
}

/* ── Section E: len semantics ── */
static void test_len_semantics(void)
{
    char dst[4];
    char src[4];

    /* len == 0 must not touch the destination buffer */
    dst[0] = (char)0xEE;
    lakai_asciitoakai((char *)"AB", dst, 0);
    check((unsigned char)dst[0] == 0xEE, "lakai_asciitoakai(len=0) leaves dst untouched");

    /* partial len converts only the first `len` bytes */
    dst[0] = (char)0xEE;
    dst[1] = (char)0xEE;
    src[0] = 'A';
    src[1] = 'B';
    lakai_asciitoakai(src, dst, 1);
    check((unsigned char)dst[0] == 11, "lakai_asciitoakai(len=1) converts first byte ('A'->11)");
    check((unsigned char)dst[1] == 0xEE, "lakai_asciitoakai(len=1) leaves trailing byte untouched");

    /* akai->ascii len == 0 must not touch the destination buffer */
    dst[0] = (char)0xEE;
    lakai_akaitoascii((char *)"\x0b", dst, 0);
    check((unsigned char)dst[0] == 0xEE, "lakai_akaitoascii(len=0) leaves dst untouched");
}

/* ── Section F: lakai_init / lakai_open / lakai_close contract ── */
static void test_handle_contract(void)
{
    LHANDLE h;

    /* init is idempotent / safe to call more than once */
    lakai_init();
    lakai_init();
    check(1, "lakai_init() is idempotent (called twice without crash)");

    /* no device is open yet -> closing slot 0 must fail */
    check(lakai_close(0) == -1, "lakai_close(0) with no open device returns -1");

    /* opening a nonexistent device must fail (negative handle) */
    h = lakai_open((char *)"/nonexistent/lakai-test-device");
    check(h < 0, "lakai_open(nonexistent device) returns negative (failure)");

    /* a second failed open must not corrupt library state */
    h = lakai_open((char *)"/nonexistent/lakai-test-device-2");
    check(h < 0, "lakai_open(second nonexistent device) still fails cleanly");

    /* still nothing open -> closing slot 0 remains a failure */
    check(lakai_close(0) == -1, "lakai_close(0) after failed opens still returns -1");
}

/* ── Section G: published header constants (ABI contract) ── */
static void test_header_constants(void)
{
    check(S2000_MODE == 0x09, "S2000_MODE == 0x09");
    check(S2000_SEND == 0x0c, "S2000_SEND == 0x0c");
    check(S2000_STATUS == 0x0d, "S2000_STATUS == 0x0d");
    check(S2000_RECEIVE == 0x0e, "S2000_RECEIVE == 0x0e");
    check(LAKAI_MODE_NORMAL == 0x00, "LAKAI_MODE_NORMAL == 0x00");
    check(LAKAI_MODE_SCSI_MIDI == 0x01, "LAKAI_MODE_SCSI_MIDI == 0x01");
    check(LAKAI_MODE_SCSI_BULK == 0x02, "LAKAI_MODE_SCSI_BULK == 0x02");
}

/* ── Section H: CLI executability ── */
static void check_one_cli(const char *dir, const char *name)
{
    char path[1024];
    char out[4096];
    char dev[1024];
    char listfile[1024];
    int rc = 0;
    char label[160];

    snprintf(path, sizeof(path), "%s/%s", dir, name);
    snprintf(dev, sizeof(dev), "%s", "/nonexistent/lakai-cli-device");
    snprintf(listfile, sizeof(listfile), "%s/lakai-cli-test.list", dir);

    /* (1) no arguments -> usage on stderr/stdout + non-zero exit */
    {
        char *argv[2];
        argv[0] = path;
        argv[1] = NULL;
        rc = -1;
        run_capture(argv, out, sizeof(out), &rc);
        snprintf(label, sizeof(label), "%s (no args) exits non-zero", name);
        check(rc != 0, label);
        snprintf(label, sizeof(label), "%s (no args) prints \"Usage:\"", name);
        check(strstr(out, "Usage:") != NULL, label);
    }

    /* (2) nonexistent device -> recognizable error, no crash (exit 5) */
    {
        char *argv[4];
        argv[0] = path;
        argv[1] = dev;
        if (strcmp(name, "lakclear") == 0)
        {
            argv[2] = NULL;
        }
        else
        {
            argv[2] = listfile;
            argv[3] = NULL;
        }
        rc = -1;
        run_capture(argv, out, sizeof(out), &rc);
        snprintf(label, sizeof(label),
                 "%s (bad device) returns recognizable error exit 5 (got %d)",
                 name, rc);
        check(rc == 5, label);
        snprintf(label, sizeof(label), "%s (bad device) prints \"Open failed\"", name);
        check(strstr(out, "Open failed") != NULL, label);
    }
}

static void test_cli_executables(const char *dir)
{
    check_one_cli(dir, "lakbak");
    check_one_cli(dir, "lakres");
    check_one_cli(dir, "lakclear");
}

int main(int argc, char *argv[])
{
    printf("== lakai 0.1 self-authored test suite ==\n");

    test_ascii_to_akai();
    test_akai_to_ascii();
    test_round_trip();
    test_len_semantics();
    test_handle_contract();
    test_header_constants();

    if (argc >= 2)
    {
        test_cli_executables(argv[1]);
    }
    else
    {
        printf("NOTE: no CLI directory argument given -> CLI checks skipped\n");
    }

    printf("assertions=%d failures=%d\n", g_assertions, g_failures);
    return g_failures == 0 ? 0 : 1;
}
