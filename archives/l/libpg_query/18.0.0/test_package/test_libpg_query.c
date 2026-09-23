#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pg_query.h"

/* Test 1: parse a simple SQL statement */
static int test_parse(void) {
    PgQueryParseResult result = pg_query_parse("SELECT 1");

    if (result.error) {
        fprintf(stderr, "ERROR: parse failed: %s\n", result.error->message);
        pg_query_free_parse_result(result);
        return 1;
    }

    if (!result.parse_tree || strlen(result.parse_tree) == 0) {
        fprintf(stderr, "ERROR: empty parse tree\n");
        pg_query_free_parse_result(result);
        return 1;
    }

    /* Verify the parse tree contains expected fields */
    if (!strstr(result.parse_tree, "\"version\"")) {
        fprintf(stderr, "ERROR: parse tree missing 'version' field\n");
        pg_query_free_parse_result(result);
        return 1;
    }

    if (!strstr(result.parse_tree, "SelectStmt")) {
        fprintf(stderr, "ERROR: parse tree missing 'SelectStmt'\n");
        pg_query_free_parse_result(result);
        return 1;
    }

    printf("OK: pg_query_parse(\"SELECT 1\") succeeded\n");
    printf("Parse tree length: %zu\n", strlen(result.parse_tree));

    pg_query_free_parse_result(result);
    return 0;
}

/* Test 2: normalize a query with a constant value */
static int test_normalize(void) {
    PgQueryNormalizeResult result =
        pg_query_normalize("SELECT * FROM users WHERE id = 123");

    if (result.error) {
        fprintf(stderr, "ERROR: normalize failed: %s\n", result.error->message);
        pg_query_free_normalize_result(result);
        return 1;
    }

    if (!result.normalized_query || strlen(result.normalized_query) == 0) {
        fprintf(stderr, "ERROR: empty normalized query\n");
        pg_query_free_normalize_result(result);
        return 1;
    }

    /* Constants are replaced by positional parameters */
    if (!strstr(result.normalized_query, "$1")) {
        fprintf(stderr, "ERROR: normalized query missing '$1': %s\n",
                result.normalized_query);
        pg_query_free_normalize_result(result);
        return 1;
    }

    if (strstr(result.normalized_query, "123")) {
        fprintf(stderr, "ERROR: normalized query still contains constant: %s\n",
                result.normalized_query);
        pg_query_free_normalize_result(result);
        return 1;
    }

    printf("OK: pg_query_normalize returned: %s\n", result.normalized_query);

    pg_query_free_normalize_result(result);
    return 0;
}

/* Test 3: fingerprint is produced and stable across repeated calls */
static int test_fingerprint(void) {
    PgQueryFingerprintResult first = pg_query_fingerprint("SELECT 1");
    PgQueryFingerprintResult second = pg_query_fingerprint("SELECT 1");
    int failed = 0;

    if (first.error) {
        fprintf(stderr, "ERROR: fingerprint failed: %s\n", first.error->message);
        pg_query_free_fingerprint_result(first);
        pg_query_free_fingerprint_result(second);
        return 1;
    }

    if (!first.fingerprint_str || strlen(first.fingerprint_str) == 0) {
        fprintf(stderr, "ERROR: empty fingerprint\n");
        failed = 1;
    } else if (!second.fingerprint_str ||
               strcmp(first.fingerprint_str, second.fingerprint_str) != 0) {
        fprintf(stderr, "ERROR: fingerprint is not stable across calls\n");
        failed = 1;
    } else {
        printf("OK: pg_query_fingerprint(\"SELECT 1\") = %s\n",
               first.fingerprint_str);
    }

    pg_query_free_fingerprint_result(first);
    pg_query_free_fingerprint_result(second);
    return failed;
}

int main(void) {
    if (test_parse() != 0) {
        return 1;
    }
    if (test_normalize() != 0) {
        return 1;
    }
    if (test_fingerprint() != 0) {
        return 1;
    }

    printf("All 3 consumer tests passed\n");
    return 0;
}