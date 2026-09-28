/*
 * test_package for epr-api 2.3 — consumer smoke test (R34: substantive API use).
 *
 * Calls the public ENVISAT reader API: init/close, error introspection and
 * log-level setting, verifying linkage and basic runtime behaviour.
 */
#include <stdio.h>
#include <stdlib.h>

#include <epr_api.h>

int main(void) {
    int rc;

    /* 1. init the API with minimal logging, no handlers */
    rc = epr_init_api(e_log_error, NULL, NULL);
    if (rc != 0) {
        fprintf(stderr, "epr_init_api failed: %d\n", rc);
        return 1;
    }

    /* 2. nothing failed yet, so error code must be e_err_none (0) */
    if (epr_get_last_err_code() != e_err_none) {
        fprintf(stderr, "unexpected error code: %d\n", epr_get_last_err_code());
        return 2;
    }

    /* 3. set log level and query the last error message (NULL when none) */
    epr_set_log_level(e_log_warning);
    if (epr_get_last_err_message() != NULL) {
        fprintf(stderr, "unexpected error message\n");
        return 3;
    }

    /* 4. close */
    epr_close_api();

    printf("epr-api 2.3 consumer test: OK\n");
    return 0;
}