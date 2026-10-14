#include <stdio.h>
#include <string.h>

#include <libsigrok/libsigrok.h>

int main(void)
{
    struct sr_context *context = NULL;
    struct sr_dev_driver **drivers;
    const char *version = sr_package_version_string_get();
    if (!version || !strstr(version, "0.5.2"))
        return 1;
    if (sr_init(&context) != SR_OK || !context)
        return 2;
    drivers = sr_driver_list(context);
    if (!drivers || !drivers[0]) {
        sr_exit(context);
        return 3;
    }
    if (sr_exit(context) != SR_OK)
        return 4;
    printf("libsigrok %s consumer PASS\n", version);
    return 0;
}
