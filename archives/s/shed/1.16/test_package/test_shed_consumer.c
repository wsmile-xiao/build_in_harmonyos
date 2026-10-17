/*
 * Consumer tests for the packaged shed 1.16 executable.
 *
 * usage: test_shed_consumer <path-to-packaged-shed> <scratch-dir>
 *
 * Every case drives the real executable: command line contract through
 * pipes, and the full-screen editor through a pseudo terminal where keys
 * are typed and the rendered screen, the exit status and the files shed
 * writes are verified.
 */
#define _GNU_SOURCE
#include "shed_pty.h"

static const unsigned char SAMPLE[16] = {
    's', 'h', 'e', 'd', 0x00, 0x7f, 0xff, 0x0a,
    'O', 'H', 'O', 'S', '-', 'P', 'C', '!',
};

static const char *g_shed;
static char g_dir[4096];
static char g_sample[4200];

static const char *HELP_MAIN =
    "SPACE|E edit  S|W|F search  J jump to   T dec/hex   D dump     1|2|4 cursor";
static const char *HELP_KEYS =
    "X       exit  R|N   repeat  B bin edit  A ext. asc  P preview  `     endian";

static int reset_sample(void)
{
    return write_file(g_sample, SAMPLE, sizeof SAMPLE);
}

static int open_sample(term_t *t)
{
    char *argv[] = {(char *)g_shed, "sample.bin", NULL};

    if (reset_sample() != 0 || term_spawn(t, argv, g_dir, -1, NULL) != 0)
        return -1;
    return 0;
}

static int wait_status(term_t *t, unsigned cursor)
{
    char want[SCR_COLS + 1];

    expect_status(want, sizeof want, cursor, sizeof SAMPLE);
    return term_wait_row(t, STATUS_ROW, ROW_EQ, want);
}

/* type text into a prompt once the prompt is on the status row */
static int answer_prompt(term_t *t, const char *prompt, const char *text)
{
    char typed[128];

    if (!term_wait_row(t, STATUS_ROW, ROW_PREFIX, prompt))
        return 0;
    term_send(t, text);
    snprintf(typed, sizeof typed, "%s%s", prompt, text);
    if (!term_wait_row(t, STATUS_ROW, ROW_PREFIX, typed))
        return 0;
    term_send(t, "\r");
    return 1;
}

/* 1: command line contract (no terminal needed) */
static void case_cli(void)
{
    char out[4096];
    char *version[] = {(char *)g_shed, "--version", NULL};
    char *help[] = {(char *)g_shed, "--help", NULL};
    char *missing[] = {(char *)g_shed, "/nonexistent/shed-input.bin", NULL};
    char *two[] = {(char *)g_shed, "a.bin", "b.bin", NULL};
    int rc;

    rc = run_capture(version, out, sizeof out);
    check(rc == 0 && strcmp(out, "shed 1.16 (lfs)\n") == 0,
          "--version prints \"shed 1.16 (lfs)\" (large-file build) and exits 0 [rc=%d]", rc);
    rc = run_capture(help, out, sizeof out);
    check(rc == 0 && strncmp(out, "usage: shed [OPTIONS] [FILE]\n", 29) == 0 &&
              strstr(out, "-r / --readonly") != NULL,
          "--help prints the usage with --readonly and exits 0 [rc=%d]", rc);
    rc = run_capture(missing, out, sizeof out);
    check(rc == 1 && strstr(out, "could not open /nonexistent/shed-input.bin (No such file or directory)"),
          "missing file is reported with strerror and exit 1 [rc=%d]", rc);
    rc = run_capture(two, out, sizeof out);
    check(rc == 1 && strstr(out, "too many files!") != NULL,
          "two file operands are rejected with exit 1 [rc=%d]", rc);
}

/* 2: first screen of a 16-byte file */
static void case_render(void)
{
    char want[256], got[256];
    term_t t;
    long n;
    int i, ok = 1;

    if (open_sample(&t) != 0) {
        check(0, "spawn shed on a pseudo terminal");
        return;
    }
    snprintf(want, sizeof want, "%-70s%s", "sample.bin (regular file)", "shed 1.16");
    check(term_wait_row(&t, 0, ROW_EQ, want),
          "title row: file name, file type, \"shed 1.16\" at column 70 of 80");
    check(term_wait_row(&t, 1, ROW_EQ, "offs  asc hex dec oct bin"), "column header row");
    for (i = 0; i < (int)sizeof SAMPLE; i++) {
        expect_row(want, sizeof want, 4, (unsigned)i, SAMPLE[i]);
        if (!term_wait_row(&t, i + 2, ROW_EQ, want)) {
            scr_row(&t.scr, i + 2, got);
            printf("      row %d: want \"%s\" got \"%s\"\n", i + 2, want, got);
            ok = 0;
        }
    }
    check(ok, "16 byte rows show asc/hex/dec/oct/bin, non-printables blank");
    check(wait_status(&t, 0), "status row shows cursor 0/16 (dec)");
    check(term_wait_row(&t, SCR_ROWS - 2, ROW_EQ, HELP_MAIN) &&
              term_wait_row(&t, SCR_ROWS - 1, ROW_EQ, HELP_KEYS),
          "two key help rows at the bottom");
    if (g_case_failures)
        scr_dump(&t.scr);
    term_send(&t, "x");
    check(term_finish(&t) == 0, "x quits with exit status 0");
    n = read_file(g_sample, got, sizeof got);
    check(n == (long)sizeof SAMPLE && memcmp(got, SAMPLE, sizeof SAMPLE) == 0,
          "viewing leaves the file unchanged");
}

/* 3: search a byte sequence in the hex column and a string in the ascii column */
static void case_search(void)
{
    term_t t;

    if (open_sample(&t) != 0) {
        check(0, "spawn shed on a pseudo terminal");
        return;
    }
    check(wait_status(&t, 0), "editor ready at offset 0");
    term_send(&t, "\t/");
    check(answer_prompt(&t, "search for (hex): ", "7F FF") && wait_status(&t, 5),
          "hex column search \"7F FF\" moves the cursor to offset 5");
    term_send(&t, "\001/"); /* ^A: back to the ascii column */
    check(answer_prompt(&t, "search for (asc): ", "OS") && wait_status(&t, 10),
          "ascii search \"OS\" skips the \"OH\" partial match and stops at offset 10");
    if (g_case_failures)
        scr_dump(&t.scr);
    term_send(&t, "x");
    check(term_finish(&t) == 0, "x quits with exit status 0");
}

/* 4: jump + hex edit is written through to the file */
static void case_edit(void)
{
    unsigned char want_bytes[sizeof SAMPLE];
    char want[256], got[256];
    term_t t;
    long n;

    if (open_sample(&t) != 0) {
        check(0, "spawn shed on a pseudo terminal");
        return;
    }
    check(wait_status(&t, 0), "editor ready at offset 0");
    term_send(&t, "j");
    check(answer_prompt(&t, "jump to (dec): ", "3") && wait_status(&t, 3),
          "j 3 jumps to offset 3");
    term_send(&t, "\te");
    check(answer_prompt(&t, "new value (hex): ", "7a"), "e in the hex column asks for a hex value");
    expect_row(want, sizeof want, 4, 3, 0x7a);
    check(term_wait_row(&t, 5, ROW_EQ, want), "row of offset 3 now reads z/7A/122/172/01111010");
    if (g_case_failures)
        scr_dump(&t.scr);
    term_send(&t, "x");
    check(term_finish(&t) == 0, "x quits with exit status 0");
    memcpy(want_bytes, SAMPLE, sizeof SAMPLE);
    want_bytes[3] = 0x7a;
    n = read_file(g_sample, got, sizeof got);
    check(n == (long)sizeof SAMPLE && memcmp(got, want_bytes, sizeof SAMPLE) == 0,
          "file on disk: byte 3 is 0x7A, the other 15 bytes and the size are unchanged");
}

/* 5: the dump command writes a text table that we parse back */
static void case_dump(void)
{
    char path[4300], want[2048], got[2048], bits[9];
    size_t len = 0;
    term_t t;
    long n;
    int i;

    snprintf(path, sizeof path, "%s/dump.txt", g_dir);
    unlink(path);
    if (open_sample(&t) != 0) {
        check(0, "spawn shed on a pseudo terminal");
        return;
    }
    check(wait_status(&t, 0), "editor ready at offset 0");
    term_send(&t, "d");
    check(answer_prompt(&t, "dump to file: ", "dump.txt"), "d asks for the dump file name");
    check(term_wait_row(&t, SCR_ROWS - 2, ROW_EQ, HELP_MAIN), "back in the main view after dumping");
    if (g_case_failures)
        scr_dump(&t.scr);
    term_send(&t, "x");
    check(term_finish(&t) == 0, "x quits with exit status 0");

    len += (size_t)snprintf(want + len, sizeof want - len, "offs  asc hex dec oct bin\n");
    for (i = 0; i < (int)sizeof SAMPLE; i++) {
        unsigned b = SAMPLE[i];

        len += (size_t)snprintf(want + len, sizeof want - len, "%04d:  %c  %02X  %03u %03o %s\n", i,
                                (b > 32 && b < 127) ? (char)b : ' ', b, b, b, bin8(b, bits));
    }
    n = read_file(path, got, sizeof got - 1);
    if (n >= 0)
        got[n] = 0;
    check(n == (long)len && memcmp(got, want, len) == 0,
          "dump.txt holds the header and 16 exact rows (%ld bytes, want %zu)", n, len);
}

int main(int argc, char **argv)
{
    static const struct {
        const char *name;
        void (*run)(void);
    } cases[] = {
        {"cli_contract", case_cli},
        {"screen_render", case_render},
        {"search_hex_and_ascii", case_search},
        {"jump_edit_persist", case_edit},
        {"dump_to_file", case_dump},
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
    snprintf(g_dir, sizeof g_dir, "%s/consumer", argv[2]);
    snprintf(g_sample, sizeof g_sample, "%s/sample.bin", g_dir);
    if (reset_dir(g_dir) != 0) {
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
    printf("shed consumer tests: %d/%d passed\n", total - failed, total);
    return failed ? 1 : 0;
}
