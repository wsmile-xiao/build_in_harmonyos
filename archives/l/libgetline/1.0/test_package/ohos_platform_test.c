/* libgetline 1.0 — HarmonyOS platform test (OHOS 专项测试).
 *
 * Verifies the public API's state-flag and error semantics against the
 * OHOS (musl-based) libc, exercising real read(2)/open(2)/fd lifecycle:
 *   1. NOBLANK suppresses a blank line by returning 0 WITHOUT setting EOF;
 *      a plain context returns the blank line as a single-newline line.
 *   2. LIBGETLN_ST_EOF is reported through libgetln_get_state after
 *      exhaustion; clear_state clears NOBLANK/VERBOSE but EOF is sticky
 *      (the upstream mask keeps LIBGETLN_ST_EOF always set).
 *   3. NOCLOSE keeps the descriptor open after libgetln_free_context.
 *   4. getline on a context with no file fails with SIZE_MAX and errno EBADF.
 *   5. Lines longer than the context buffer grow the caller's buffer.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libgetline.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                                        \
    do {                                                                        \
        if (!(cond)) {                                                          \
            fprintf(stderr, "OHOS FAIL: %s\n", msg);                            \
            ++g_failures;                                                       \
        }                                                                       \
    } while (0)

static void write_tmp_file(const char *path, const char *content)
{
    FILE *f = fopen(path, "w");
    if (f != NULL) {
        fputs(content, f);
        fclose(f);
    }
}

int main(void)
{
    const char *path = "ohos-input.txt";
    struct libgetln_context *ctx = NULL;
    char *line = NULL;
    size_t cap = 0;
    unsigned int state = 0;
    int fd = -1;
    size_t n;

    write_tmp_file(path, "first\n\nthird\n");

    /* 1: NOBLANK suppresses the blank line by returning 0 without EOF. */
    ctx = libgetln_new_context(16, LIBGETLN_ST_NOBLANK);
    CHECK(ctx != NULL, "NOBLANK context created");
    CHECK(libgetln_open_file(ctx, path) == 0, "NOBLANK: open file");
    n = libgetln_getline(ctx, &line, &cap);
    CHECK(n == 6 && line[0] == 'f', "NOBLANK: first line read");
    n = libgetln_getline(ctx, &line, &cap);
    CHECK(n == 0, "NOBLANK: blank line returns 0");
    state = 0;
    libgetln_get_state(ctx, &state);
    CHECK(!(state & LIBGETLN_ST_EOF), "NOBLANK: suppression does not set EOF");
    n = libgetln_getline(ctx, &line, &cap);
    CHECK(n == 6 && line[0] == 't', "NOBLANK: third line read after suppression");
    CHECK(libgetln_getline(ctx, &line, &cap) == 0, "NOBLANK: EOF after last line");
    CHECK(libgetln_free_context(ctx, NULL) == 0, "NOBLANK: free context");

    /* 1b: without NOBLANK the blank line is returned as a one-newline line. */
    ctx = libgetln_new_context(16, 0);
    CHECK(libgetln_open_file(ctx, path) == 0, "plain: open file");
    CHECK(libgetln_getline(ctx, &line, &cap) == 6, "plain: first line read");
    n = libgetln_getline(ctx, &line, &cap);
    CHECK(n == 1 && line[0] == '\n', "plain: blank line returned as newline");
    CHECK(libgetln_getline(ctx, &line, &cap) == 6, "plain: third line read");
    CHECK(libgetln_free_context(ctx, NULL) == 0, "plain: free context");

    /* 2: EOF flag reported after exhaustion; clear_state semantics. */
    ctx = libgetln_new_context(16, 0);
    CHECK(libgetln_open_file(ctx, path) == 0, "EOF: open file");
    while (libgetln_getline(ctx, &line, &cap) > 0) {
    }
    CHECK(libgetln_get_state(ctx, &state) == 0 && (state & LIBGETLN_ST_EOF),
          "EOF: LIBGETLN_ST_EOF set after exhaustion");
    CHECK(libgetln_set_state(ctx, LIBGETLN_ST_NOBLANK | LIBGETLN_ST_VERBOSE) == 0,
          "EOF: set_state returns 0");
    CHECK(libgetln_clear_state(ctx, LIBGETLN_ST_NOBLANK | LIBGETLN_ST_VERBOSE) == 0,
          "EOF: clear_state returns 0");
    CHECK(libgetln_get_state(ctx, &state) == 0
              && !(state & (LIBGETLN_ST_NOBLANK | LIBGETLN_ST_VERBOSE))
              && (state & LIBGETLN_ST_EOF),
          "EOF: NOBLANK/VERBOSE cleared while EOF stays set");
    CHECK(libgetln_clear_state(ctx, LIBGETLN_ST_EOF) == 0,
          "EOF: clear_state(EOF) returns 0");
    CHECK(libgetln_get_state(ctx, &state) == 0 && (state & LIBGETLN_ST_EOF),
          "EOF: EOF flag is sticky (upstream mask keeps it set)");
    CHECK(libgetln_free_context(ctx, NULL) == 0, "EOF: free context");

    /* 3: NOCLOSE pins the descriptor across free_context. */
    ctx = libgetln_new_context(16, LIBGETLN_ST_NOCLOSE);
    CHECK(libgetln_open_file(ctx, path) == 0, "NOCLOSE: open file");
    fd = libgetln_get_file(ctx);
    CHECK(fd >= 0, "NOCLOSE: valid fd");
    CHECK(libgetln_free_context(ctx, NULL) == 0, "NOCLOSE: free context");
    {
        char buf[8];
        ssize_t r = read(fd, buf, sizeof(buf));
        CHECK(r > 0, "NOCLOSE: fd still readable after free_context");
    }
    close(fd);

    /* 4: getline without an open file -> SIZE_MAX with errno EBADF. */
    ctx = libgetln_new_context(16, 0);
    errno = 0;
    CHECK(libgetln_getline(ctx, &line, &cap) == (size_t)-1,
          "no-file: getline returns SIZE_MAX");
    CHECK(errno == EBADF, "no-file: errno is EBADF");
    CHECK(libgetln_free_context(ctx, NULL) == 0, "no-file: free context");

    /* 5: buffer growth for a line longer than the context buffer. */
    write_tmp_file(path, "");
    {
        FILE *f = fopen(path, "w");
        int i;
        if (f != NULL) {
            for (i = 0; i < 200; ++i)
                fputc('x', f);
            fputc('\n', f);
            fclose(f);
        }
    }
    ctx = libgetln_new_context(4, 0);
    CHECK(libgetln_open_file(ctx, path) == 0, "growth: open long-line file");
    n = libgetln_getline(ctx, &line, &cap);
    CHECK(n == 201, "growth: 200-char line plus newline read");
    CHECK(cap >= 201, "growth: caller buffer grew beyond the initial size");
    CHECK(libgetln_free_context(ctx, NULL) == 0, "growth: free context");

    free(line);
    remove(path);

    if (g_failures != 0) {
        fprintf(stderr, "OHOS platform test FAILED: %d check(s)\n", g_failures);
        return 1;
    }
    printf("OHOS platform test OK: NOBLANK/EOF/NOCLOSE/EBADF/growth verified\n");
    return 0;
}