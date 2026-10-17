/* Upstream checkmsva integration path, made deterministic with mock_msva.py. */
#include <stdio.h>
#include <string.h>

#include <msv/msv.h>

static int checks;

#define CHECK(condition, message) do {                            \
    if (!(condition)) {                                          \
        fprintf(stderr, "FAIL: %s (line %d)\n", message, __LINE__); \
        return 1;                                                \
    }                                                            \
    ++checks;                                                    \
} while (0)

int main(void) {
    msv_ctxt_t context = msv_ctxt_init(NULL);
    CHECK(context != NULL, "msv_ctxt_init from environment");
    CHECK(msv_check_msva(context) == LIBMSV_ERROR_SUCCESS,
          "msv_check_msva protocol and availability");

    struct msv_query query = {
        "https",
        "server",
        "www.softwarefreedom.org",
        "x509pem",
        "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n"
    };
    struct msv_response *response = NULL;
    CHECK(msv_query_agent(context, query, &response) ==
              LIBMSV_ERROR_SUCCESS,
          "msv_query_agent accepted certificate use");
    CHECK(response != NULL, "query returned response");
    CHECK(response->valid == 1, "response is valid");
    CHECK(response->message != NULL &&
              strcmp(response->message, "deterministic MSVA reply") == 0,
          "response message parsed");

    msv_response_destroy(response);
    msv_ctxt_destroy(context);
    printf("PASS: upstream MSVA integration path (%d checks)\n", checks);
    return 0;
}
