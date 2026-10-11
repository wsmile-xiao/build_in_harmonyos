#include <rokuecp.h>

#include <stdio.h>
#include <string.h>

#ifndef __OHOS__
#error "HarmonyOS-specific test must be compiled by the OHOS toolchain"
#endif

int main(void)
{
    RokuDevice device;
    memset(&device, 0, sizeof(device));

    if (sizeof(void *) != 8) {
        fprintf(stderr, "expected 64-bit HarmonyOS PC ABI\n");
        return 1;
    }
    if (rokuSendKey(&device, "VolumeMute") != -1) {
        fprintf(stderr, "installed rokuecp API returned an unexpected value\n");
        return 1;
    }

    puts("HarmonyOS ABI/API check: 1/1 passed");
    return 0;
}
