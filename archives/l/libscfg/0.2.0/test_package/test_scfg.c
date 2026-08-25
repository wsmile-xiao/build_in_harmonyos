/* test_scfg.c — libscfg 0.2.0 consumer test
 *
 * Real functional test: calls libscfg's actual API to parse, verify, and
 * round-trip-format a configuration, then frees it. Uses fmemopen() so it
 * never touches the filesystem (avoids OHOS /tmp read-only pitfalls).
 *
 * API exercised (from scfg.h):
 *   - scfg_parse_file(block, FILE*)      parse a config from a FILE*
 *   - scfg_format_file(block, FILE*)     format a block back to a FILE*
 *   - scfg_block_finish(block)           free a parsed block
 *
 * Assertions:
 *   1. parse succeeds (returns 0)
 *   2. top-level directive count == 3
 *   3. directive[0].name == "listen", params == {"tcp", "8080"}
 *   4. directive[1].name == "host", has 2 children ("db" / "cache")
 *   5. directive[2].name == "timeout", params == {"30"}
 *   6. round-trip: format → re-parse → structure identical
 *   7. scfg_block_finish runs without crash
 */
#define _POSIX_C_SOURCE 200809L
#include <scfg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            fprintf(stderr, "FAIL: %s (line %d)\n", (msg), __LINE__);      \
            failures++;                                                     \
        } else {                                                            \
            printf("ok: %s\n", (msg));                                      \
        }                                                                   \
    } while (0)

static int streq(const char *a, const char *b) {
    return (a && b) ? (strcmp(a, b) == 0) : (a == b);
}

/* Sample configuration in scfg format (directive [params...] [{ children }]). */
static const char SAMPLE[] =
    "listen tcp 8080\n"
    "host 0.0.0.0 {\n"
    "    db 127.0.0.1\n"
    "    cache ttl 60\n"
    "}\n"
    "timeout 30\n";

int main(void) {
    struct scfg_block block;
    memset(&block, 0, sizeof(block));

    /* --- 1. parse --- */
    FILE *in = fmemopen((void *)SAMPLE, sizeof(SAMPLE) - 1, "r");
    if (!in) {
        fprintf(stderr, "FAIL: fmemopen for parse (line %d)\n", __LINE__);
        return 1;
    }
    int rc = scfg_parse_file(&block, in);
    fclose(in);
    CHECK(rc == 0, "scfg_parse_file returns 0");

    /* --- 2. directive count --- */
    CHECK(block.directives_len == 3, "top-level directive count == 3");
    if (block.directives_len < 3) {
        fprintf(stderr, "aborting: too few directives (%zu)\n", block.directives_len);
        scfg_block_finish(&block);
        return 1;
    }

    /* --- 3. directive[0]: listen tcp 8080 --- */
    struct scfg_directive *d0 = &block.directives[0];
    CHECK(streq(d0->name, "listen"), "d0 name == listen");
    CHECK(d0->params_len == 2, "d0 params_len == 2");
    if (d0->params_len >= 2) {
        CHECK(streq(d0->params[0], "tcp"), "d0 param0 == tcp");
        CHECK(streq(d0->params[1], "8080"), "d0 param1 == 8080");
    }
    CHECK(d0->children.directives_len == 0, "d0 has no children");

    /* --- 4. directive[1]: host { db / cache } --- */
    struct scfg_directive *d1 = &block.directives[1];
    CHECK(streq(d1->name, "host"), "d1 name == host");
    CHECK(d1->params_len == 1, "d1 params_len == 1");
    if (d1->params_len >= 1) {
        CHECK(streq(d1->params[0], "0.0.0.0"), "d1 param0 == 0.0.0.0");
    }
    CHECK(d1->children.directives_len == 2, "d1 has 2 children");
    if (d1->children.directives_len >= 2) {
        struct scfg_directive *c0 = &d1->children.directives[0];
        struct scfg_directive *c1 = &d1->children.directives[1];
        CHECK(streq(c0->name, "db"), "d1 child0 name == db");
        CHECK(streq(c1->name, "cache"), "d1 child1 name == cache");
        if (c1->params_len >= 1) {
            CHECK(streq(c1->params[0], "ttl"), "d1 child1 param0 == ttl");
        }
        if (c1->params_len >= 2) {
            CHECK(streq(c1->params[1], "60"), "d1 child1 param1 == 60");
        }
    }

    /* --- 5. directive[2]: timeout 30 --- */
    struct scfg_directive *d2 = &block.directives[2];
    CHECK(streq(d2->name, "timeout"), "d2 name == timeout");
    CHECK(d2->params_len == 1, "d2 params_len == 1");
    if (d2->params_len >= 1) {
        CHECK(streq(d2->params[0], "30"), "d2 param0 == 30");
    }

    /* --- 6. round-trip: format → re-parse → compare structure --- */
    char buf[4096];
    FILE *out = fmemopen(buf, sizeof(buf), "w");
    if (!out) {
        fprintf(stderr, "FAIL: fmemopen for format\n");
        failures++;
    } else {
        rc = scfg_format_file(&block, out);
        fflush(out);
        long formatted_len = ftell(out);
        fclose(out);
        CHECK(rc == 0, "scfg_format_file returns 0");
        CHECK(formatted_len > 0, "formatted output is non-empty");

        if (formatted_len > 0) {
            /* fmemopen 'r' needs a null-terminated buffer for some impls;
               scfg_parse_file reads via fgets so a bounded buffer is fine,
               but terminate defensively. */
            if (formatted_len < (long)sizeof(buf)) {
                buf[formatted_len] = '\0';
            }
            struct scfg_block block2;
            memset(&block2, 0, sizeof(block2));
            FILE *in2 = fmemopen(buf, (size_t)formatted_len, "r");
            if (in2) {
                int rc2 = scfg_parse_file(&block2, in2);
                fclose(in2);
                CHECK(rc2 == 0, "round-trip re-parse returns 0");
                if (rc2 == 0) {
                    CHECK(block2.directives_len == block.directives_len,
                          "round-trip directive count matches");
                    if (block2.directives_len >= 1) {
                        CHECK(streq(block2.directives[0].name, "listen"),
                              "round-trip d0 name == listen");
                        CHECK(block2.directives[0].params_len == 2,
                              "round-trip d0 params_len == 2");
                    }
                    if (block2.directives_len >= 2) {
                        CHECK(block2.directives[1].children.directives_len == 2,
                              "round-trip d1 children count == 2");
                    }
                    if (block2.directives_len >= 3) {
                        CHECK(streq(block2.directives[2].name, "timeout"),
                              "round-trip d2 name == timeout");
                    }
                }
                scfg_block_finish(&block2);
            } else {
                fprintf(stderr, "FAIL: fmemopen for round-trip parse\n");
                failures++;
            }
        }
    }

    /* --- 7. free --- */
    scfg_block_finish(&block);
    printf("ok: scfg_block_finish (no crash)\n");

    if (failures > 0) {
        fprintf(stderr, "\n%d assertion(s) FAILED\n", failures);
        return 1;
    }
    printf("\nALL ASSERTIONS PASSED\n");
    return 0;
}
