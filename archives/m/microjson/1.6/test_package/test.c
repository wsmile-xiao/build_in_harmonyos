/* test_package/test.c — Conan L1 test for microjson
 *
 * Parses JSON objects using the microjson API and verifies results.
 * Exits 0 on success, 1 on failure.
 *
 * SPDX-License-Identifier: BSD-2-Clause
 */
#include <stdio.h>
#include <stdbool.h>
#include <string.h>

#include "mjson.h"

/* File-scope variables (addresses are compile-time constants) */
static int count;
static bool flag1, flag2;
static char name[64];

static const struct json_attr_t attrs1[] = {
    {"count",  t_integer, .addr.integer = &count},
    {"flag1",  t_boolean, .addr.boolean = &flag1},
    {"flag2",  t_boolean, .addr.boolean = &flag2},
    {NULL},
};

static const struct json_attr_t attrs2[] = {
    {"name", t_string, .addr.string = name, .len = sizeof(name)},
    {NULL},
};

int main(void) {
    /* Test 1: Parse a simple JSON object */
    const char *json1 = "{\"count\": 42, \"flag1\": true, \"flag2\": false}";

    int status = json_read_object(json1, attrs1, NULL);
    if (status != 0) {
        fprintf(stderr, "json_read_object failed: %s\n", json_error_string(status));
        return 1;
    }

    if (count != 42) {
        fprintf(stderr, "count mismatch: expected 42, got %d\n", count);
        return 1;
    }
    if (!flag1) {
        fprintf(stderr, "flag1 should be true\n");
        return 1;
    }
    if (flag2) {
        fprintf(stderr, "flag2 should be false\n");
        return 1;
    }

    /* Test 2: Parse a string value */
    const char *json2 = "{\"name\": \"hello\"}";

    status = json_read_object(json2, attrs2, NULL);
    if (status != 0) {
        fprintf(stderr, "json_read_object (string) failed: %s\n", json_error_string(status));
        return 1;
    }

    if (strcmp(name, "hello") != 0) {
        fprintf(stderr, "name mismatch: expected 'hello', got '%s'\n", name);
        return 1;
    }

    printf("microjson L1 test passed: count=%d, flag1=%d, flag2=%d, name=%s\n",
           count, flag1, flag2, name);
    return 0;
}
