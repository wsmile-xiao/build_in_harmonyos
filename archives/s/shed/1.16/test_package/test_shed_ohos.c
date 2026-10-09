/*
 * HarmonyOS-specific consumer tests for the packaged shed 1.16 executable.
 *
 * usage: test_shed_ohos <path-to-packaged-shed> <scratch-dir>
 *
 * `producer | shed` buffers the piped bytes in a temporary file.  Upstream
 * used tmpfile(), which the OHOS musl hard-wires to /data/local/tmp (not
 * writable for ordinary processes, $TMPDIR ignored), so piped input always
 * died with "tmpfile() failed.".  The adapted shed (patches/0001) creates the
 * buffer with mkstemp() + unlink() in $TMPDIR.  These cases run the packaged
 * executable with its stdin on a pipe and its terminal on a pseudo tty.
 */
#define _GNU_SOURCE
#include "shed_pty.h"

static const unsigned char DATA[16] = {
    's', 'h', 'e', 'd', 0x00, 0x7f, 0xff, 0x0a,
    'O', 'H', 'O', 'S', '-', 'P', 'C', '!',
};

static const char *g_shed;
static char g_dir[4096];
static char g_tmp[4200];

/* shed reading stdin from a pipe; returns the pipe's write end or -1 */
static int spawn_piped(term_t *t, const char *tmpdir)
{
    char *argv[] = {(char *)g_shed, NULL};
    int p[2];

    if (pipe2(p, O_CLOEXEC) != 0)
        return -1;
    if (term_spawn(t, argv, g_dir, p[0], tmpdir) != 0) {
        close(p[0]);
        close(p[1]);
        return -1;
    }
    close(p[0]);
    return p[1];
}

/* 1: piped bytes are buffered in $TMPDIR and shown read-only */
static void case_pipe(void)
{
    char want[256], got[256];
    term_t t;
    int wfd, i, ok = 1, entries;

    wfd = spawn_piped(&t, g_tmp);
    if (wfd < 0) {
        check(0, "spawn shed with stdin on a pipe");
        return;
    }
    check(write(wfd, DATA, sizeof DATA) == (ssize_t)sizeof DATA, "16 bytes written into the pipe");
    close(wfd);

    snprintf(want, sizeof want, "%-70s%s", "(stdin) (read only)", "shed 1.16");
    check(term_wait_row(&t, 0, ROW_EQ, want), "title row reads \"(stdin) (read only)\" - no tmpfile() abort");
    snprintf(want, sizeof want, "%-18s%s", "offset", "asc hex dec oct bin");
    check(term_wait_row(&t, 1, ROW_EQ, want), "column header for the 16-digit stdin offsets");
    for (i = 0; i < (int)sizeof DATA; i++) {
        expect_row(want, sizeof want, 16, (unsigned)i, DATA[i]);
        if (!term_wait_row(&t, i + 2, ROW_EQ, want)) {
            scr_row(&t.scr, i + 2, got);
            printf("      row %d: want \"%s\" got \"%s\"\n", i + 2, want, got);
            ok = 0;
        }
    }
    check(ok, "all 16 piped bytes rendered from the $TMPDIR buffer");
    expect_status(want, sizeof want, 0, sizeof DATA);
    check(term_wait_row(&t, STATUS_ROW, ROW_EQ, want), "status row counts 16 bytes of input");
    entries = dir_entries(g_tmp);
    check(entries == 0, "buffer file is anonymous: $TMPDIR has no entry while shed runs [%d]", entries);
    if (g_case_failures)
        scr_dump(&t.scr);
    term_send(&t, "x");
    check(term_finish(&t) == 0, "keys typed on the tty still work with stdin on a pipe: x exits 0");
    entries = dir_entries(g_tmp);
    check(entries == 0, "nothing left behind in $TMPDIR after exit [%d]", entries);
}

/* 2: the buffer really goes to $TMPDIR: a missing $TMPDIR is reported */
static void case_tmpdir_honoured(void)
{
    char missing[4300];
    term_t t;
    int wfd, rc;

    snprintf(missing, sizeof missing, "%s/missing", g_tmp);
    wfd = spawn_piped(&t, missing);
    if (wfd < 0) {
        check(0, "spawn shed with stdin on a pipe");
        return;
    }
    close(wfd);
    rc = term_finish(&t);
    check(rc == 1, "shed exits 1 when $TMPDIR does not exist [rc=%d]", rc);
    check(strstr(t.log, "shed: tmpfile() failed (No such file or directory).") != NULL,
          "error names the errno of the $TMPDIR buffer: \"%s\"", t.log);
    check(dir_entries(g_tmp) == 0, "no stray file created elsewhere in the scratch $TMPDIR");
}

int main(int argc, char **argv)
{
    static const struct {
        const char *name;
        void (*run)(void);
    } cases[] = {
        {"stdin_pipe_buffered_in_tmpdir", case_pipe},
        {"tmpdir_honoured_for_stdin_buffer", case_tmpdir_honoured},
    };
    int i, failed = 0, total = (int)(sizeof cases / sizeof cases[0]);

    if (argc != 3) {
        fprintf(stderr, "usage: %s <path-to-shed> <scratch-dir>\n", argv[0]);
        return 2;
    }
    signal(SIGPIPE, SIG_IGN);
    setvbuf(stdout, NULL, _IOLBF, 0);
    g_shed = argv[1];
    if (mkdir(argv[2], 0755) != 0 && errno != EEXIST) {
        perror(argv[2]);
        return 2;
    }
    snprintf(g_dir, sizeof g_dir, "%s/ohos", argv[2]);
    snprintf(g_tmp, sizeof g_tmp, "%s/tmp", g_dir);
    if (reset_dir(g_dir) != 0 || reset_dir(g_tmp) != 0) {
        perror(g_dir);
        return 2;
    }
    for (i = 0; i < total; i++) {
        g_case_failures = 0;
        printf("[case] %s\n", cases[i].name);
        cases[i].run();
        printf("[%s] %s\n", g_case_failures ? "FAIL" : "PASS", cases[i].name);
        if (g_case_failures)
            failed++;
    }
    printf("shed OHOS-specific tests: %d/%d passed\n", total - failed, total);
    return failed ? 1 : 0;
}
