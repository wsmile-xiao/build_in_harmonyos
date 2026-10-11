#include <rokuecp.h>

#include <stdio.h>
#include <string.h>

static int checks;

#define CHECK(expression)                                                        \
    do {                                                                         \
        ++checks;                                                                \
        if (!(expression)) {                                                     \
            fprintf(stderr, "check %d failed: %s\n", checks, #expression);     \
            return 1;                                                            \
        }                                                                        \
    } while (0)

int main(void)
{
    RokuDevice device;
    RokuTVChannel channel;
    RokuExtTVChannel active_channel;
    RokuApp apps[1];
    RokuSearchParams search;
    const char *names[] = {"key"};
    const char *values[] = {"value"};

    memset(&device, 0, sizeof(device));
    memset(&channel, 0, sizeof(channel));
    memset(&active_channel, 0, sizeof(active_channel));
    memset(apps, 0, sizeof(apps));
    memset(&search, 0, sizeof(search));

    CHECK(rokuSendKey(&device, "VolumeUp") == -1);
    device.isLimited = true;
    CHECK(rokuSendKey(&device, "Home") == -2);

    device.isLimited = false;
    CHECK(getRokuTVChannels(&device, 1, &channel) == -4);
    device.isTV = true;
    device.isLimited = true;
    CHECK(getRokuTVChannels(&device, 1, &channel) == -5);

    device.isTV = false;
    device.isLimited = false;
    CHECK(getActiveRokuTVChannel(&device, &active_channel) == -3);
    device.isTV = true;
    device.isLimited = true;
    CHECK(getActiveRokuTVChannel(&device, &active_channel) == -4);

    device.isTV = false;
    device.isLimited = false;
    CHECK(launchRokuTVChannel(&device, &channel) == -2);
    device.isLimited = true;
    CHECK(getRokuApps(&device, 1, apps) == -4);

    device.isLimited = false;
    device.hasSearchSupport = false;
    CHECK(rokuSearch(&device, "Roku", &search) == -1);
    device.isLimited = true;
    CHECK(sendCustomRokuInput(&device, 1, names, values) == -1);

    printf("rokuecp API checks: %d/10 passed\n", checks);
    return checks == 10 ? 0 : 1;
}
