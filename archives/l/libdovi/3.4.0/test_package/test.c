#include <stdio.h>
#include <stdint.h>
#include <string.h>

#if __has_include(<libdovi/rpu_parser.h>)
#include <libdovi/rpu_parser.h>
#elif __has_include("rpu_parser.h")
#include "rpu_parser.h"
#else
#include <rpu_parser.h>
#endif

/* Consumer test: exercise the real libdovi C-API (R34).
 * Uses only deterministic error-path checks so no external RPU
 * fixture files are required:
 *  1. dovi_parse_rpu(NULL, 0) must return an invalid object with an error
 *  2. dovi_parse_rpu(garbage, len) must fail parsing with an error set
 *  3. dovi_convert_rpu_with_mode(NULL, 2) must return -1
 *  4. dovi_write_rpu on an invalid object must return NULL
 *  5. free helpers must tolerate NULL without crashing
 */
int main(void) {
    int checks_passed = 0;
    const int checks_total = 5;

    /* 1. null buffer */
    DoviRpuOpaque *null_obj = dovi_parse_rpu((const uint8_t *)0, 0);
    if (null_obj != 0) {
        const char *err = dovi_rpu_get_error(null_obj);
        if (err != 0 && err[0] != '\0') {
            printf("CHECK-OK: null buffer rejected: %s\n", err);
            checks_passed++;
        } else {
            printf("CHECK-FAIL: null buffer error string missing\n");
        }
        dovi_rpu_free(null_obj);
    } else {
        printf("CHECK-FAIL: dovi_parse_rpu(NULL) returned NULL\n");
    }

    /* 2. garbage buffer */
    static const uint8_t garbage[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
    };
    DoviRpuOpaque *bad = dovi_parse_rpu(garbage, sizeof(garbage));
    if (bad != 0) {
        const char *err = dovi_rpu_get_error(bad);
        if (err != 0 && err[0] != '\0') {
            printf("CHECK-OK: garbage buffer rejected: %s\n", err);
            checks_passed++;
        } else {
            printf("CHECK-FAIL: garbage buffer error string missing\n");
        }
        /* 4. write on invalid object must return NULL */
        const DoviData *data = dovi_write_rpu(bad);
        if (data == 0) {
            printf("CHECK-OK: dovi_write_rpu(invalid) returned NULL\n");
            checks_passed++;
        } else {
            printf("CHECK-FAIL: dovi_write_rpu(invalid) should be NULL\n");
            dovi_data_free(data);
        }
        dovi_rpu_free(bad);
    } else {
        printf("CHECK-FAIL: dovi_parse_rpu(garbage) returned NULL\n");
    }

    /* 3. convert with NULL handle */
    if (dovi_convert_rpu_with_mode((DoviRpuOpaque *)0, 2) == -1) {
        printf("CHECK-OK: convert(NULL) returned -1\n");
        checks_passed++;
    } else {
        printf("CHECK-FAIL: convert(NULL) should return -1\n");
    }

    /* 5. NULL-tolerant frees */
    dovi_rpu_free((DoviRpuOpaque *)0);
    dovi_rpu_list_free((const DoviRpuOpaqueList *)0);
    dovi_data_free((const DoviData *)0);
    printf("CHECK-OK: NULL frees did not crash\n");
    checks_passed++;

    printf("libdovi consumer test: %d/%d checks passed\n", checks_passed, checks_total);
    if (checks_passed != checks_total) {
        printf("CONSUMER-FAIL\n");
        return 1;
    }
    printf("CONSUMER-PASS\n");
    return 0;
}
