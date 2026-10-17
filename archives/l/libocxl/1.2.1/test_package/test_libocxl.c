// Consumer test for the installed libocxl package.
//
// Covers the deterministic, hardware independent part of the public API.  The
// device-facing calls (AFU open/attach, MMIO) need an OpenCAPI accelerator; the
// failed-open paths are checked here instead.
#include <stdio.h>
#include <string.h>

#include <libocxl.h>

static int checks;
static int failures;

static void quiet_handler(ocxl_err error, const char *message)
{
    (void)error;
    (void)message;
}

static void check(int ok, const char *what)
{
    checks++;
    if (ok) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);

    check(strcmp(ocxl_err_to_string(OCXL_OK), "OK") == 0,
          "ocxl_err_to_string(OCXL_OK) == 'OK'");
    check(strcmp(ocxl_err_to_string(OCXL_NO_MEM), "No memory") == 0,
          "ocxl_err_to_string(OCXL_NO_MEM) == 'No memory'");
    check(strcmp(ocxl_err_to_string(OCXL_INVALID_ARGS), "Invalid arguments") == 0,
          "ocxl_err_to_string(OCXL_INVALID_ARGS) == 'Invalid arguments'");
    check(strcmp(ocxl_err_to_string((ocxl_err)1234), "Unknown error") == 0,
          "ocxl_err_to_string(unknown) == 'Unknown error'");

    ocxl_enable_messages(OCXL_ERRORS);
    ocxl_set_error_message_handler(quiet_handler);
    check(1, "ocxl_enable_messages/ocxl_set_error_message_handler are callable");

    const char *info = ocxl_info();
    check(info != NULL && strlen(info) > 0, "ocxl_info() returns a non-empty string");
    check(info != NULL && strstr(info, "LibOCXL Version: 1.2.1") != NULL,
          "ocxl_info() reports version 1.2.1");

    ocxl_afu_h afu = OCXL_INVALID_AFU;
    ocxl_err err = ocxl_afu_open_from_dev("/nonexistent/ocxl/device_pasid0", &afu);
    check(err != OCXL_OK && afu == OCXL_INVALID_AFU,
          "ocxl_afu_open_from_dev(nonexistent path) fails and leaves afu NULL");

    afu = OCXL_INVALID_AFU;
    err = ocxl_afu_open("no-such-afu-name", &afu);
    check(err != OCXL_OK && afu == OCXL_INVALID_AFU,
          "ocxl_afu_open(no-such-afu) fails and leaves afu NULL");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures ? 1 : 0;
}
