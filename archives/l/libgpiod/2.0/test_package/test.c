/* test_package/test.c — libgpiod 2.0 consumer test
 *
 * Calls actual libgpiod API functions to verify the library is correctly
 * built and linkable. No GPIO hardware required — we only test object
 * creation and release which are pure software operations.
 */
#include <stdio.h>
#include <stdlib.h>

/* libgpiod 2.x API header */
#include <gpiod.h>

int main(void) {
    int ret = 0;

    /* Test 1: Create a line config object and free it */
    struct gpiod_line_config *line_cfg = gpiod_line_config_new();
    if (line_cfg == NULL) {
        fprintf(stderr, "FAIL: gpiod_line_config_new() returned NULL\n");
        return 1;
    }
    gpiod_line_config_free(line_cfg);
    printf("PASS: gpiod_line_config_new() / gpiod_line_config_free()\n");

    /* Test 2: Create a request config object and free it */
    struct gpiod_request_config *req_cfg = gpiod_request_config_new();
    if (req_cfg == NULL) {
        fprintf(stderr, "FAIL: gpiod_request_config_new() returned NULL\n");
        return 1;
    }
    gpiod_request_config_free(req_cfg);
    printf("PASS: gpiod_request_config_new() / gpiod_request_config_free()\n");

    /* Test 3: Check library API version string is available */
    const char *version = gpiod_api_version();
    if (version == NULL) {
        fprintf(stderr, "FAIL: gpiod_api_version() returned NULL\n");
        return 1;
    }
    printf("PASS: gpiod_api_version() = %s\n", version);

    printf("All tests passed.\n");
    return ret;
}
