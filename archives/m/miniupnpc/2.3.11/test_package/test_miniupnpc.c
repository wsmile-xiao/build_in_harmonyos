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

    int error = 0;
    struct UPNPDev *devlist = upnpDiscover(1, NULL, NULL, 0, 0, 2, &error);
    printf("upnpDiscover returned: %p, error: %d\n", (void *)devlist, error);
    if (devlist) {
        freeUPNPDevlist(devlist);
    }
    printf("PASS: upnpDiscover callable\n");
    printf("OK: miniupnpc API test passed\n");
    return 0;
}
