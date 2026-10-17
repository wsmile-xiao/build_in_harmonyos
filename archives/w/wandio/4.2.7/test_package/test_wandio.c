/* test_package/test_wandio.c -- wandio 4.2.7 consumer test (OpenHarmony/aarch64).
 *
 * Exercises the portable core API with zero optional compression backends:
 *  1. compression-type lookup (known names resolve, unknown returns NULL)
 *  2. compression-type detection from file extensions (pure string logic)
 *  3. plain-file write/read roundtrip via wandio_wcreate / wandio_create
 *  4. printf/fgets/tell/seek/peek on a plain-text file
 *
 * Prints HMBS hard-gate markers with counts sourced from the same
 * tests_run/tests_failed counters as the Results line. Exit 0 on all-pass.
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "wandio.h"

static int tests_run = 0;
static int tests_failed = 0;

#define RUN(fn) do { \
    printf("[run] %s\n", #fn); \
    tests_run++; \
    if (fn() != 0) { \
        tests_failed++; \
        printf("        [FAIL] %s\n", #fn); \
    } else { \
        printf("        [ok] %s\n", #fn); \
    } \
} while (0)

static int test_lookup(void) {
    struct wandio_compression_type *t;

    t = wandio_lookup_compression_type("gzip");
    if (t == NULL) {
        fprintf(stderr, "lookup gzip returned NULL\n");
        return 1;
    }
    if (strcmp(t->ext, "gz") != 0 || t->compress_type != WANDIO_COMPRESS_ZLIB) {
        fprintf(stderr, "lookup gzip mismatch: ext=%s type=%d\n", t->ext, t->compress_type);
        return 2;
    }
    t = wandio_lookup_compression_type("zstd");
    if (t == NULL || t->compress_type != WANDIO_COMPRESS_ZSTD) {
        fprintf(stderr, "lookup zstd failed\n");
        return 3;
    }
    if (wandio_lookup_compression_type("no-such-method") != NULL) {
        fprintf(stderr, "lookup of unknown method should return NULL\n");
        return 4;
    }
    return 0;
}

static int test_detect(void) {
    if (wandio_detect_compression_type("trace.gz") != WANDIO_COMPRESS_ZLIB) {
        fprintf(stderr, "detect .gz failed\n");
        return 1;
    }
    if (wandio_detect_compression_type("trace.zst") != WANDIO_COMPRESS_ZSTD) {
        fprintf(stderr, "detect .zst failed\n");
        return 2;
    }
    if (wandio_detect_compression_type("trace.txt") != WANDIO_COMPRESS_NONE) {
        fprintf(stderr, "detect plain suffix should be NONE\n");
        return 3;
    }
    return 0;
}

static const char *tmp_path(char *buf, size_t cap, const char *name) {
    const char *dir = getenv("TMPDIR");
    if (dir == NULL || dir[0] == '\0') {
        dir = "/tmp";
    }
    snprintf(buf, cap, "%s/%s", dir, name);
    return buf;
}

static int test_roundtrip(void) {
    static const char payload[] = "wandio-harmonyos-roundtrip-0123456789\nsecond-line\n";
    char path[1024];
    iow_t *w;
    io_t *r;
    char readback[256];
    int64_t written, total = 0, n;

    tmp_path(path, sizeof(path), "wandio_rt.txt");
    unlink(path);
    w = wandio_wcreate(path, WANDIO_COMPRESS_NONE, 0, O_WRONLY | O_CREAT | O_TRUNC);
    if (w == NULL) {
        fprintf(stderr, "wandio_wcreate failed\n");
        return 1;
    }
    written = wandio_wwrite(w, payload, (int64_t)(sizeof(payload) - 1));
    if (written != (int64_t)(sizeof(payload) - 1)) {
        fprintf(stderr, "short write: %lld\n", (long long)written);
        wandio_wdestroy(w);
        return 2;
    }
    wandio_wdestroy(w);

    r = wandio_create(path);
    if (r == NULL) {
        fprintf(stderr, "wandio_create failed\n");
        return 3;
    }
    while (total < (int64_t)(sizeof(readback) - 1)) {
        n = wandio_read(r, readback + total, (int64_t)(sizeof(readback) - 1) - total);
        if (n < 0) {
            fprintf(stderr, "wandio_read error\n");
            wandio_destroy(r);
            return 4;
        }
        if (n == 0) {
            break;
        }
        total += n;
    }
    wandio_destroy(r);
    unlink(path);
    if (total != (int64_t)(sizeof(payload) - 1) ||
        memcmp(readback, payload, (size_t)total) != 0) {
        fprintf(stderr, "roundtrip content mismatch: got %lld bytes\n", (long long)total);
        return 5;
    }
    return 0;
}

static int test_text_api(void) {
    /* NOTE: wandio_tell forwards to the stdio child after read-ahead
     * (ior-peek.c peek_tell), so it reports the file size, not 0.
     * Peek must leave it unchanged; assert stability, not absolute 0. */
    char path[1024];
    iow_t *w;
    io_t *r;
    char line[128];
    char peekbuf[5];
    int64_t n, pos, pos_before;

    tmp_path(path, sizeof(path), "wandio_text.txt");
    unlink(path);
    w = wandio_wcreate(path, WANDIO_COMPRESS_NONE, 0, O_WRONLY | O_CREAT | O_TRUNC);
    if (w == NULL) {
        fprintf(stderr, "wcreate for text api failed\n");
        return 1;
    }
    if (wandio_printf(w, "hello %s %d\n", "wandio", 427) <= 0) {
        fprintf(stderr, "wandio_printf failed\n");
        wandio_wdestroy(w);
        return 2;
    }
    wandio_wdestroy(w);

    r = wandio_create_uncompressed(path);
    if (r == NULL) {
        fprintf(stderr, "create_uncompressed failed\n");
        return 3;
    }
    pos_before = wandio_tell(r);
    if (pos_before < 0) {
        fprintf(stderr, "tell before peek failed: %lld\n", (long long)pos_before);
        wandio_destroy(r);
        return 4;
    }
    n = wandio_peek(r, peekbuf, (int64_t)sizeof(peekbuf));
    if (n != (int64_t)sizeof(peekbuf) || memcmp(peekbuf, "hello", 5) != 0) {
        fprintf(stderr, "peek mismatch\n");
        wandio_destroy(r);
        return 4;
    }
    pos = wandio_tell(r);
    if (pos < 0 || pos != pos_before) {
        fprintf(stderr, "tell changed across peek: before=%lld after=%lld\n",
                (long long)pos_before, (long long)pos);
        wandio_destroy(r);
        return 5;
    }
    n = wandio_fgets(r, line, (int64_t)sizeof(line), 1);
    if (n <= 0 || strcmp(line, "hello wandio 427") != 0) {
        fprintf(stderr, "fgets mismatch: n=%lld line=%s\n", (long long)n, line);
        wandio_destroy(r);
        return 6;
    }
    if (wandio_seek(r, 0, SEEK_SET) != 0) {
        fprintf(stderr, "seek to 0 failed\n");
        wandio_destroy(r);
        return 7;
    }
    n = wandio_read(r, line, 5);
    if (n != 5 || memcmp(line, "hello", 5) != 0) {
        fprintf(stderr, "read after seek mismatch\n");
        wandio_destroy(r);
        return 8;
    }
    wandio_destroy(r);
    unlink(path);
    return 0;
}

int main(void) {
    int discovered = 4;
    int executed, passed, failed, skipped = 0;

    /* Synchronous IO keeps the roundtrip deterministic on every platform. */
    setenv("LIBTRACEIO", "nothreads", 1);

    printf("=== wandio 4.2.7 test_package (OpenHarmony/aarch64) ===\n");
    RUN(test_lookup);
    RUN(test_detect);
    RUN(test_roundtrip);
    RUN(test_text_api);

    executed = tests_run;
    failed = tests_failed;
    passed = tests_run - tests_failed;

    printf("\n=== Results: %d/%d passed, %d failed ===\n", passed, executed, failed);
    printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"autotools\",\"command\":\"make check (no TESTS target)\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0,\"reason\":\"upstream 4.2.7 ships no TESTS/check target; see test_package MANIFEST audit\"}\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_wandio\",\"discovered\":%d,\"passedCount\":%d}\n",
           (failed == 0) ? "true" : "false", discovered, passed);
    (void)skipped;

    if (failed == 0) {
        printf("All wandio consumer tests PASSED.\n");
        return 0;
    }
    printf("%d test(s) FAILED.\n", failed);
    return 1;
}
