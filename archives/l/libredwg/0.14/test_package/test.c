#include <stdio.h>
#include <string.h>
#include <dwg.h>

/* Consumer test for libredwg: verify headers, version macros and
   basic error-path API (no test-data file needed). */
int main(void) {
    int failures = 0;

    /* 1. Version macros must match 0.14 */
    if (LIBREDWG_VERSION_MAJOR != 0 || LIBREDWG_VERSION_MINOR != 14) {
        fprintf(stderr, "FAIL: version macros %d.%d, expected 0.14\n",
                LIBREDWG_VERSION_MAJOR, LIBREDWG_VERSION_MINOR);
        failures++;
    } else {
        printf("PASS: version macros 0.14 (LIBREDWG_VERSION=%d)\n",
               LIBREDWG_VERSION);
    }

    /* 2. Dwg_Data struct must be usable (zero-init + size check) */
    {
        Dwg_Data dwg;
        memset(&dwg, 0, sizeof(dwg));
        if (sizeof(dwg) == 0) {
            fprintf(stderr, "FAIL: Dwg_Data has zero size\n");
            failures++;
        } else {
            printf("PASS: Dwg_Data size %u\n", (unsigned)sizeof(dwg));
        }
        /* 3. Reading a missing file must fail cleanly (error path) */
        {
            int err = dwg_read_file("/nonexistent-libredwg-test.dwg", &dwg);
            if (err == 0) {
                fprintf(stderr, "FAIL: dwg_read_file unexpectedly succeeded\n");
                failures++;
            } else {
                printf("PASS: dwg_read_file error path returns %d\n", err);
            }
            dwg_free(&dwg);
            printf("PASS: dwg_free on error-path object\n");
        }
    }

    if (failures) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("PASS: all libredwg consumer assertions\n");
    return 0;
}
