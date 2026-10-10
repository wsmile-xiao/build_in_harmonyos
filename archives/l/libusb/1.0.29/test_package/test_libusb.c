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

    /* R40: 覆盖平台相关初始化路径。
     * OHOS 沙箱内 sysfs/netlink 受限，libusb_init_context 配合
     * LIBUSB_OPTION_NO_DEVICE_DISCOVERY 是唯一可用初始化方式。 */
    const struct libusb_init_option options[] = {
        { LIBUSB_OPTION_NO_DEVICE_DISCOVERY, { .ival = 1 } },
    };
    libusb_context *ctx = NULL;
    int rc = libusb_init_context(&ctx, options, 1);
    if (rc != 0) {
        fprintf(stderr, "libusb_init_context failed: %d (%s)\n",
                rc, libusb_error_name(rc));
        return 5;
    }
    libusb_exit(ctx);

    printf("libusb consumer smoke passed: %u.%u.%u\n",
           version->major, version->minor, version->micro);
    return 0;
}
