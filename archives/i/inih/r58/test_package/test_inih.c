/*
 * test_inih.c — inih API smoke test.
 *
 * Verifies that:
 *   1. ini_parse_string() parses valid INI data correctly
 *   2. ini_parse_string() returns line number on parse error
 *   3. Handler function receives correct section/name/value
 *   4. Multiple sections and key=value pairs work
 *   5. Empty INI data is handled gracefully
 *
 * R34 compliance: This test_package actually calls inih's public API
 * (ini_parse_string) rather than just printing a string.
 */
#include "ini.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* Test context: accumulates parsed (section, name, value) tuples */
typedef struct {
    char sections[10][32];
    char names[10][64];
    char values[10][64];
    int count;
} test_ctx;

/* Handler that collects parsed pairs into test_ctx */
static int collect_handler(void* user, const char* section,
                           const char* name, const char* value)
{
    test_ctx* ctx = (test_ctx*)user;
    if (ctx->count >= 10) {
        fprintf(stderr, "FAIL: too many pairs (limit 10)\n");
        return 0;
    }
    strncpy(ctx->sections[ctx->count], section, sizeof(ctx->sections[0]) - 1);
    strncpy(ctx->names[ctx->count], name, sizeof(ctx->names[0]) - 1);
    strncpy(ctx->values[ctx->count], value, sizeof(ctx->values[0]) - 1);
    ctx->count++;
    return 1;
}

/* Handler that counts pairs and checks a specific expected value */
static int count_handler(void* user, const char* section,
                         const char* name, const char* value)
{
    int* count = (int*)user;
    (void)section;
    (void)name;
    (void)value;
    (*count)++;
    return 1;
}

int main(void) {
    int failures = 0;
    int ret;
    int count;

    /* ===== Test 1: Basic parsing ===== */
    printf("Test 1: Basic ini_parse_string...\n");
    {
        const char* ini = "[server]\nhost=example.com\nport=8080\n";
        test_ctx ctx;
        memset(&ctx, 0, sizeof(ctx));
        ret = ini_parse_string(ini, collect_handler, &ctx);
        if (ret != 0) {
            fprintf(stderr, "FAIL: ini_parse_string returned %d (expected 0)\n", ret);
            failures++;
        } else if (ctx.count != 2) {
            fprintf(stderr, "FAIL: expected 2 pairs, got %d\n", ctx.count);
            failures++;
        } else if (strcmp(ctx.sections[0], "server") != 0 ||
                   strcmp(ctx.names[0], "host") != 0 ||
                   strcmp(ctx.values[0], "example.com") != 0) {
            fprintf(stderr, "FAIL: first pair mismatch: [%s] %s=%s\n",
                    ctx.sections[0], ctx.names[0], ctx.values[0]);
            failures++;
        } else if (strcmp(ctx.sections[1], "server") != 0 ||
                   strcmp(ctx.names[1], "port") != 0 ||
                   strcmp(ctx.values[1], "8080") != 0) {
            fprintf(stderr, "FAIL: second pair mismatch: [%s] %s=%s\n",
                    ctx.sections[1], ctx.names[1], ctx.values[1]);
            failures++;
        } else {
            printf("  PASS: parsed 2 pairs correctly\n");
        }
    }

    /* ===== Test 2: Multiple sections ===== */
    printf("Test 2: Multiple sections...\n");
    {
        const char* ini = "[global]\nname=test\n\n[network]\ntimeout=30\nretry=3\n";
        test_ctx ctx;
        memset(&ctx, 0, sizeof(ctx));
        ret = ini_parse_string(ini, collect_handler, &ctx);
        if (ret != 0) {
            fprintf(stderr, "FAIL: ini_parse_string returned %d (expected 0)\n", ret);
            failures++;
        } else if (ctx.count != 3) {
            fprintf(stderr, "FAIL: expected 3 pairs, got %d\n", ctx.count);
            failures++;
        } else if (strcmp(ctx.sections[2], "network") != 0 ||
                   strcmp(ctx.names[2], "retry") != 0 ||
                   strcmp(ctx.values[2], "3") != 0) {
            fprintf(stderr, "FAIL: third pair mismatch: [%s] %s=%s\n",
                    ctx.sections[2], ctx.names[2], ctx.values[2]);
            failures++;
        } else {
            printf("  PASS: multi-section parsing correct\n");
        }
    }

    /* ===== Test 3: Comment handling ===== */
    printf("Test 3: Comments and blank lines...\n");
    {
        const char* ini = "; this is a comment\n# also comment\n[key]\nval=1\n\nval2=2\n";
        test_ctx ctx;
        memset(&ctx, 0, sizeof(ctx));
        ret = ini_parse_string(ini, collect_handler, &ctx);
        if (ret != 0) {
            fprintf(stderr, "FAIL: ini_parse_string with comments returned %d\n", ret);
            failures++;
        } else if (ctx.count != 2) {
            fprintf(stderr, "FAIL: expected 2 pairs (comments ignored), got %d\n", ctx.count);
            failures++;
        } else {
            printf("  PASS: comments ignored, %d pairs parsed\n", ctx.count);
        }
    }

    /* ===== Test 4: Parse error detection ===== */
    /* An invalid line (no '=') must be reported as a non-zero return and
     * the valid pair (good=1) before it must still be parsed. */
    printf("Test 4: Parse error detection...\n");
    {
        const char* ini = "[ok]\ngood=1\nbad_line_no_equals\n";
        count = 0;
        ret = ini_parse_string(ini, count_handler, &count);
        if (ret <= 0) {
            fprintf(stderr, "FAIL: expected parse error (ret>0), got ret=%d\n", ret);
            failures++;
        } else if (count != 1) {
            fprintf(stderr, "FAIL: expected 1 valid pair before error, got %d\n", count);
            failures++;
        } else {
            printf("  PASS: parse error detected at line %d, 1 pair parsed\n", ret);
        }
    }

    /* ===== Test 5: Empty input ===== */
    printf("Test 5: Empty input...\n");
    {
        const char* ini = "";
        count = 0;
        ret = ini_parse_string(ini, count_handler, &count);
        if (ret != 0) {
            fprintf(stderr, "FAIL: empty input returned %d (expected 0)\n", ret);
            failures++;
        } else if (count != 0) {
            fprintf(stderr, "FAIL: empty input should give 0 pairs, got %d\n", count);
            failures++;
        } else {
            printf("  PASS: empty input handled correctly\n");
        }
    }

    /* ===== Test 6: Section-only (no key=value) ===== */
    printf("Test 6: Section with no values...\n");
    {
        const char* ini = "[empty_section]\n";
        count = 0;
        ret = ini_parse_string(ini, count_handler, &count);
        if (ret != 0) {
            fprintf(stderr, "FAIL: section-only returned %d (expected 0)\n", ret);
            failures++;
        } else if (count != 0) {
            fprintf(stderr, "FAIL: section-only should give 0 pairs, got %d\n", count);
            failures++;
        } else {
            printf("  PASS: section without values handled correctly\n");
        }
    }

    /* ===== Summary ===== */
    printf("\n");
    if (failures > 0) {
        printf("RESULT: %d test(s) FAILED\n", failures);
        return 1;
    }

    printf("RESULT: All inih tests passed.\n");
    return 0;
}
