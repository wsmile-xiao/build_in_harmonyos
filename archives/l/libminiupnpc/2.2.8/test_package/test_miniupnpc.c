#include <stdio.h>
#include <string.h>
#include "miniupnpc/miniupnpc.h"

int main(void) {
    const char *ver = MINIUPNPC_VERSION;
    if (ver == NULL || ver[0] == '\0') {
        printf("FAIL: empty MINIUPNPC_VERSION\n");
        return 1;
    }
    printf("PASS: version non-empty: %s\n", ver);

    int error = -1;
    struct UPNPDev *devlist = upnpDiscover(1, NULL, NULL, 0, 0, 2, &error);
    printf("upnpDiscover returned: %p, error: %d\n", (void *)devlist, error);
    /* Semantic assertion: with a 1 ms discovery timeout in a no-UPnP-device
     * environment the call must return promptly with the error variable
     * written (UPNPDISCOVER_SUCCESS=0 when no error occurred, devlist NULL
     * because no device answered within 1 ms — any CI host without an
     * SSDP gateway deterministically produces this outcome). */
    if (devlist == NULL && error != 0) {
        printf("FAIL: upnpDiscover no-device path: error=%d (expected 0)\n",
               error);
        return 1;
    }
    if (devlist != NULL) {
        /* A stray SSDP responder on the worker network: free path must work. */
        freeUPNPDevlist(devlist);
    }
    printf("PASS: upnpDiscover no-device smoke (error=%d)\n", error);
    printf("OK: miniupnpc API test passed\n");
    return 0;
}
