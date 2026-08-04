#include <libusb.h>

#include <stdio.h>

int main(void)
{
    const struct libusb_version *version = libusb_get_version();
    if (version == NULL) {
        fprintf(stderr, "libusb_get_version returned NULL\n");
        return 1;
    }
    if (version->major != 1 || version->minor != 0) {
        fprintf(stderr, "unexpected libusb version: %u.%u.%u\n",
                version->major, version->minor, version->micro);
        return 2;
    }
    if (libusb_error_name(LIBUSB_ERROR_ACCESS) == NULL) {
        fprintf(stderr, "libusb_error_name failed\n");
        return 3;
    }
    if (libusb_strerror(LIBUSB_ERROR_NOT_SUPPORTED) == NULL) {
        fprintf(stderr, "libusb_strerror failed\n");
        return 4;
    }

    printf("libusb consumer smoke passed: %u.%u.%u\n",
           version->major, version->minor, version->micro);
    return 0;
}
