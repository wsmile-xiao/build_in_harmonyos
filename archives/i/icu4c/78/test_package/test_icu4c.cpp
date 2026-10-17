/*
 * test_icu4c.cpp — Conan L1 test for icu4c 78
 *
 * Calls ICU C API to verify the library is correctly built and functional:
 * - u_init() initializes ICU
 * - u_getUnicodeVersion() retrieves Unicode version data
 * - u_errorName() verifies error handling API
 *
 * R34: test must call real ICU API, not just print a string.
 */
#include <unicode/utypes.h>
#include <unicode/uchar.h>
#include <unicode/uclean.h>
#include <stdio.h>
#include <string.h>

int main() {
    UErrorCode status = U_ZERO_ERROR;

    /* Initialize ICU — this loads data and verifies the library works */
    u_init(&status);
    if (U_FAILURE(status)) {
        printf("FAIL: u_init() failed: %s\n", u_errorName(status));
        return 1;
    }
    printf("OK: u_init() succeeded\n");

    /* Get Unicode version — verifies data library is linked correctly */
    UVersionInfo uver = {0};
    u_getUnicodeVersion(uver);
    printf("OK: Unicode version %d.%d.%d.%d\n",
           uver[0], uver[1], uver[2], uver[3]);
    if (uver[0] == 0) {
        printf("FAIL: Unicode version is zero — data not loaded\n");
        return 1;
    }

    /* Verify error name API — basic ICU common library function */
    const char *err_name = u_errorName(U_BUFFER_OVERFLOW_ERROR);
    if (err_name && strstr(err_name, "BUFFER_OVERFLOW") != NULL) {
        printf("OK: u_errorName() returns: %s\n", err_name);
    } else {
        printf("FAIL: u_errorName() returned unexpected value\n");
        return 1;
    }

    /* Verify uchar API — character property lookup */
    if (u_isalpha(0x0041)) {  /* 'A' */
        printf("OK: u_isalpha('A') = true\n");
    } else {
        printf("FAIL: u_isalpha('A') returned false\n");
        return 1;
    }

    printf("All ICU tests passed.\n");
    return 0;
}
