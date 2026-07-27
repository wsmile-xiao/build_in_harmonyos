#include <stdio.h>
#include <string.h>
#include "miniupnpc/miniupnpc.h"

int main(void) {
    /* Verify the version string is accessible from the library header */
    printf("miniupnpc version: %s\n", MINIUPNPC_VERSION);

    /* Call upnpDiscover with 1ms delay — exercises the library's
       socket and network code path without requiring actual devices. */
    int error = 0;
    struct UPNPDev *devlist = upnpDiscover(1, NULL, NULL, 0, 0, 2, &error);
    printf("upnpDiscover returned: %p, error: %d\n", (void *)devlist, error);

    if (devlist) {
        freeUPNPDevlist(devlist);
    }

    /* Verify the expected version */
    if (strcmp(MINIUPNPC_VERSION, "2.3.3") == 0) {
        printf("OK: miniupnpc 2.3.3 API test passed\n");
        return 0;
    } else {
        printf("FAIL: unexpected version\n");
        return 1;
    }
}
