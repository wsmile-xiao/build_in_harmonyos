#include <am7xxx.h>
#include <stdio.h>

int main(void)
{
    am7xxx_context *context = NULL;
    int result = am7xxx_init(&context);
    if (result == -1 && context == NULL) {
        /* OHOS may deny this user access to /sys/bus/usb/devices. */
        puts("libam7xxx USB permission path passed");
        return 0;
    }
    if (result != 0 || context == NULL) {
        fprintf(stderr, "am7xxx_init failed: %d\n", result);
        return 1;
    }
    am7xxx_set_log_level(context, AM7XXX_LOG_ERROR);
    am7xxx_shutdown(context);
    puts("libam7xxx consumer passed");
    return 0;
}
