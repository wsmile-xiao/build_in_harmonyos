/*
 * test_afl.c — AFLplusplus test_package header-ABI test.
 *
 * Verifies that the packaged AFL++ headers (include/afl) are installed and
 * usable from consumer code, and that the key type/macro definitions that
 * define AFL++'s ABI contract are accessible and correct. The companion
 * test_target.c + test() exercise the packaged binaries themselves.
 */
#include <stdio.h>
#include <string.h>

#include "config.h"
#include "types.h"
#include "common.h"

int main(void) {
    int failures = 0;

    /* 1. VERSION string is defined and non-empty. */
    if (VERSION == NULL || strlen(VERSION) == 0) {
        fprintf(stderr, "FAIL: VERSION is empty or NULL\n");
        failures++;
    } else {
        printf("PASS: VERSION = %s\n", VERSION);
    }

    /* 2. VERSION carries the upstream source revision (v4.33c). */
    if (VERSION == NULL || strstr(VERSION, "4.33c") == NULL) {
        fprintf(stderr, "FAIL: VERSION does not contain 4.33c\n");
        failures++;
    } else {
        printf("PASS: VERSION contains 4.33c\n");
    }

    /* 3. Core types (u8/u32/u64) have expected sizes. */
    if (sizeof(u8) != 1) {
        fprintf(stderr, "FAIL: sizeof(u8) = %zu, expected 1\n", sizeof(u8));
        failures++;
    } else {
        printf("PASS: sizeof(u8) == 1\n");
    }
    if (sizeof(u32) != 4) {
        fprintf(stderr, "FAIL: sizeof(u32) = %zu, expected 4\n", sizeof(u32));
        failures++;
    } else {
        printf("PASS: sizeof(u32) == 4\n");
    }
    if (sizeof(u64) != 8) {
        fprintf(stderr, "FAIL: sizeof(u64) = %zu, expected 8\n", sizeof(u64));
        failures++;
    } else {
        printf("PASS: sizeof(u64) == 8\n");
    }
    /* 4. MAP_SIZE is defined and reasonable (1 << 16 = 65536). */
    if (MAP_SIZE != (1U << 16)) {
        fprintf(stderr, "FAIL: MAP_SIZE = %u, expected %u\n",
                (unsigned)MAP_SIZE, 1U << 16);
        failures++;
    } else {
        printf("PASS: MAP_SIZE == 1 << 16\n");
    }

    if (failures > 0) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test_afl PASSED\n");
    return 0;
}
