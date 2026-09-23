#include <stdio.h>
#include <string.h>
#include "miniupnpc/miniupnpc.h"
#include "miniupnpc/upnpreplyparse.h"

int main(void) {
    static const char response[] =
        "<root>"
        "<NewExternalIPAddress>203.0.113.10</NewExternalIPAddress>"
        "<NewExternalPort>8080</NewExternalPort>"
        "</root>";
    struct NameValueParserData parsed = {0};
    const char *external_ip;
    const char *external_port;

    printf("miniupnpc version: %s\n", MINIUPNPC_VERSION);

    if (strcmp(MINIUPNPC_VERSION, "2.3.3") != 0) {
        printf("FAIL: unexpected version\n");
        return 1;
    }

    /* Exercise a deterministic public parsing API without requiring a UPnP
       gateway or external network access. */
    ParseNameValue(response, (int)(sizeof(response) - 1), &parsed);
    external_ip = GetValueFromNameValueList(&parsed, "NewExternalIPAddress");
    external_port = GetValueFromNameValueList(&parsed, "NewExternalPort");

    if (external_ip == NULL || strcmp(external_ip, "203.0.113.10") != 0 ||
        external_port == NULL || strcmp(external_port, "8080") != 0) {
        printf("FAIL: UPnP response parsing test failed\n");
        ClearNameValueList(&parsed);
        return 1;
    }

    printf("OK: miniupnpc 2.3.3 parsing API test passed\n");
    ClearNameValueList(&parsed);
    return 0;
}
