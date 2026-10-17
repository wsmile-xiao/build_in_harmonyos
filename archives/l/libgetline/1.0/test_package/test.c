/* libgetline 1.0 — consumer test.
 *
 * A business-style consumer: reads a real file line by line through the
 * installed package's public header (libgetline.h) and public API
 * (libgetln_new_context / libgetln_open_file / libgetln_getline /
 * libgetln_free_context), verifying line content and counts plus the
 * trailing-newline convention of the returned lengths.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libgetline.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                                        \
    do {                                                                        \
        if (!(cond)) {                                                          \
            fprintf(stderr, "FAIL: %s\n", msg);                                 \
            ++g_failures;                                                       \
        }                                                                       \
    } while (0)

static const char *const INPUT_PATH = "consumer-input.txt";
static const char *const LINES[] = {
    "alpha",
    "beta",
    "gamma",
    "last-no-newline",
};
static const char *const CONTENT = "alpha\nbeta\ngamma\nlast-no-newline";

int main(void)
{
    FILE *in = NULL;
    struct libgetln_context *ctx = NULL;
    char *line = NULL;
    size_t cap = 0;
    size_t n;
    int idx = 0;
    int matched = 1;

    in = fopen(INPUT_PATH, "w");
    CHECK(in != NULL, "create input file");
    if (in == NULL)
        return 1;
    fputs(CONTENT, in);
    CHECK(fclose(in) == 0, "close input file");

    ctx = libgetln_new_context(8, LIBGETLN_ST_VERBOSE);
    CHECK(ctx != NULL, "libgetln_new_context returns non-NULL");

    CHECK(libgetln_open_file(ctx, INPUT_PATH) == 0, "libgetln_open_file returns 0");
    CHECK(libgetln_get_file(ctx) >= 0, "libgetln_get_file returns a valid fd");

    /* Four lines; each of the first three ends with '\n' (5 or 6 chars), the
     * last one has no trailing newline. */
    while (idx < 4 && (n = libgetln_getline(ctx, &line, &cap)) > 0) {
        size_t expected_len = strlen(LINES[idx]) + (idx < 3 ? 1 : 0);
        CHECK(n == expected_len, "line length includes a trailing newline when present");
        if (line[n - 1] == '\n')
            line[n - 1] = '\0';
        if (strcmp(line, LINES[idx]) != 0)
            matched = 0;
        ++idx;
    }
    CHECK(idx == 4, "all four lines were read");
    CHECK(matched == 1, "every line content matches the source file");
    CHECK(libgetln_getline(ctx, &line, &cap) == 0, "getline returns 0 at EOF");

    free(line);
    CHECK(libgetln_free_context(ctx, NULL) == 0, "libgetln_free_context returns 0");
    remove(INPUT_PATH);

    if (g_failures != 0) {
        fprintf(stderr, "consumer test FAILED: %d check(s)\n", g_failures);
        return 1;
    }
    printf("consumer test OK: read 4 lines via libgetln_getline and verified content\n");
    return 0;
}