/* HarmonyOS-specific ABI and public error-contract verification. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <msv/msv.h>

#ifndef __OHOS__
#error "test_ohos must be compiled by the HarmonyOS toolchain"
#endif

static int checks;

#define CHECK(condition, message) do {                            \
    if (!(condition)) {                                          \
        fprintf(stderr, "FAIL: %s (line %d)\n", message, __LINE__); \
        return 1;                                                \
    }                                                            \
    ++checks;                                                    \
} while (0)

int main(void) {
    struct msv_response *response = NULL;
    struct msv_query empty_query = {NULL, NULL, NULL, NULL, NULL};

    CHECK(sizeof(void *) == 8, "HarmonyOS PC uses the 64-bit ABI");
    CHECK(msv_check_msva(NULL) == LIBMSV_ERROR_BADARG,
          "NULL context is rejected");
    CHECK(msv_query_agent(NULL, empty_query, &response) ==
              LIBMSV_ERROR_BADARG,
          "query rejects a NULL context");

    msv_ctxt_t context = msv_ctxt_init("http://127.0.0.1:1");
    CHECK(context != NULL, "explicit endpoint creates context");
    CHECK(strcmp(msv_strerror(context, LIBMSV_ERROR_BADARG),
                 "Bad argument(s)") == 0,
          "error text is stable");
    CHECK(msv_query_agent(context, empty_query, &response) ==
              LIBMSV_ERROR_BADARG && response == NULL,
          "incomplete query is rejected without response allocation");
    msv_ctxt_destroy(context);

    CHECK(strstr(msv_strerror(NULL, LIBMSV_ERROR_BADARG),
                 "Unknown context") != NULL,
          "NULL-context error text is safe");
    unsetenv("MONKEYSPHERE_VALIDATION_AGENT_SOCKET");
    CHECK(msv_ctxt_init(NULL) == NULL,
          "missing endpoint environment is rejected");

    printf("PASS: HarmonyOS-specific libmsv contract (%d checks)\n", checks);
    return 0;
}
