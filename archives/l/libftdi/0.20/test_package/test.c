/*
 * libftdi consumer test.
 *
 * Links against the installed libftdi library and public headers (ftdi.h,
 * which includes <usb.h> from the libusb-compat layer) and exercises the API
 * paths that do not require FTDI hardware: context lifecycle, device
 * enumeration and the error-string reporting of a failed open.
 */
#include <stdio.h>
#include <string.h>

#include <ftdi.h>

#define CHECK(condition, message)                                        \
    do {                                                                 \
        if (condition) {                                                 \
            printf("  ok   %s\n", message);                              \
        } else {                                                         \
            printf("  FAIL %s\n", message);                              \
            failures++;                                                  \
        }                                                                \
    } while (0)

int main(void)
{
    int failures = 0;
    struct ftdi_context context;
    struct ftdi_context *fresh;
    struct ftdi_device_list *devices = NULL;
    int result;

    printf("libftdi consumer test\n");

    /* --- context lifecycle -------------------------------------------- */
    fresh = ftdi_new();
    CHECK(fresh != NULL, "ftdi_new allocates a context");
    CHECK(ftdi_init(&context) == 0, "ftdi_init succeeds");
    CHECK(strcmp(ftdi_get_error_string(NULL), "") == 0,
          "ftdi_get_error_string(NULL) returns an empty string");

    /* --- enumeration (no hardware attached in CI) --------------------- */
    result = ftdi_usb_find_all(&context, &devices, 0x0403, 0x6001);
    printf("  info ftdi_usb_find_all -> %d device(s)\n", result);
    CHECK(result >= 0, "ftdi_usb_find_all enumerates without error");
    ftdi_list_free(&devices);
    CHECK(devices == NULL, "ftdi_list_free clears the device list pointer");

    /* --- opening a non-existent device must fail cleanly -------------- */
    result = ftdi_usb_open(&context, 0x0403, 0x6001);
    printf("  info ftdi_usb_open -> %d (%s)\n", result,
           ftdi_get_error_string(&context));
    CHECK(result < 0, "ftdi_usb_open fails without an attached device");
    CHECK(strlen(ftdi_get_error_string(&context)) > 0,
          "a failed open records an error message");
    CHECK(context.usb_dev == NULL, "a failed open leaves the context closed");

    /* --- teardown ------------------------------------------------------ */
    ftdi_deinit(&context);
    if (fresh != NULL)
        ftdi_free(fresh);

    printf("consumer assertions: %d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
