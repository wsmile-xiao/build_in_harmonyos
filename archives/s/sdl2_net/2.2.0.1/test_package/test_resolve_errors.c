#include "test_common.h"

#include <string.h>

int main(void)
{
    IPaddress address;
    char invalid_host[1025];
    int status = 1;

    if (test_runtime_init() < 0) {
        return 1;
    }

    memset(invalid_host, 'a', sizeof(invalid_host) - 1);
    invalid_host[sizeof(invalid_host) - 1] = '\0';
    if (SDLNet_ResolveHost(&address, invalid_host, 23001) != -1) {
        fprintf(stderr, "Overlong host name was unexpectedly accepted\n");
        goto cleanup;
    }

    if (SDLNet_ResolveHost(&address, "127.0.0.1", 23002) < 0) {
        test_report_net_error("SDLNet_ResolveHost(numeric loopback)");
        goto cleanup;
    }
    if (SDLNet_Read32(&address.host) != 0x7f000001u ||
        SDLNet_Read16(&address.port) != 23002u) {
        fprintf(stderr, "Numeric loopback address or port is incorrect\n");
        goto cleanup;
    }

    if (SDLNet_ResolveHost(&address, NULL, 23003) < 0 ||
        SDLNet_Read16(&address.port) != 23003u) {
        test_report_net_error("SDLNet_ResolveHost(wildcard)");
        goto cleanup;
    }

    status = 0;

cleanup:
    test_runtime_quit();
    return status;
}
