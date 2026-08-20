#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <security/pam_appl.h>

#include "libpamtest.h"

#ifndef PAM_WRAPPER_TEST_LIBRARY
#error "PAM_WRAPPER_TEST_LIBRARY is not defined"
#endif

int main(void)
{
    const char *service_dir = getenv("PAM_WRAPPER_SERVICE_DIR");
    const char *tokens[] = {
        "secret",
        NULL,
    };
    struct pamtest_conv_data conv_data;
    /* pam-wrapper 1.1.8 defines run_pamtest() as a macro that passes
     * sizeof(tests) / sizeof(tests[0]) to _pamtest(); _pamtest()
     * iterates by that explicit count. The final run_pamtest()
     * argument is the optional pam_handle. */
    struct pam_testcase tests[] = {
        pam_test(PAMTEST_AUTHENTICATE, PAM_SUCCESS),
    };
    enum pamtest_err perr;
    pam_handle_t *pam_handle = NULL;
    void *handle;

    handle = dlopen(PAM_WRAPPER_TEST_LIBRARY, RTLD_LAZY);
    if (handle == NULL) {
        fprintf(stderr, "dlopen %s failed: %s\n", PAM_WRAPPER_TEST_LIBRARY, dlerror());
        return 1;
    }
    dlclose(handle);

    if (service_dir == NULL || service_dir[0] == '\0') {
        fprintf(stderr, "PAM_WRAPPER_SERVICE_DIR must be set\n");
        return 1;
    }

    memset(&conv_data, 0, sizeof(conv_data));
    conv_data.in_echo_off = tokens;

    perr = run_pamtest("matrix", "trinity", &conv_data, tests, pam_handle);
    if (perr != PAMTEST_ERR_OK || tests[0].op_rv != PAM_SUCCESS) {
        fprintf(stderr,
                "run_pamtest failed: perr=%s op_rv=%d\n",
                pamtest_strerror(perr),
                tests[0].op_rv);
        return 1;
    }

    puts("pam-wrapper libpamtest authentication check passed");
    return 0;
}
