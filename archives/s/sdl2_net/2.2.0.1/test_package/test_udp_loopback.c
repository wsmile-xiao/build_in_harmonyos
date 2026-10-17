#include "test_common.h"

#include <string.h>

int main(void)
{
    static const char payload[] = "sdl2-net-udp-loopback";
    UDPsocket sender = NULL;
    UDPsocket receiver = NULL;
    UDPpacket *outgoing = NULL;
    UDPpacket *incoming = NULL;
    IPaddress target;
    Uint32 started;
    int received = 0;
    int status = 1;

    if (test_runtime_init() < 0) {
        return 1;
    }

    receiver = SDLNet_UDP_Open(0);
    sender = SDLNet_UDP_Open(0);
    if (receiver == NULL || sender == NULL) {
        test_report_net_error("SDLNet_UDP_Open");
        goto cleanup;
    }
    if (test_udp_loopback_target(receiver, &target) < 0) {
        goto cleanup;
    }

    outgoing = SDLNet_AllocPacket((int)sizeof(payload));
    incoming = SDLNet_AllocPacket(128);
    if (outgoing == NULL || incoming == NULL) {
        test_report_net_error("SDLNet_AllocPacket");
        goto cleanup;
    }
    memcpy(outgoing->data, payload, sizeof(payload));
    outgoing->len = (int)sizeof(payload);
    outgoing->address = target;

    if (SDLNet_UDP_Send(sender, -1, outgoing) != 1) {
        test_report_net_error("SDLNet_UDP_Send");
        goto cleanup;
    }

    started = SDL_GetTicks();
    while ((SDL_GetTicks() - started) < 2000u) {
        received = SDLNet_UDP_Recv(receiver, incoming);
        if (received != 0) {
            break;
        }
        SDL_Delay(5);
    }
    if (received != 1 || incoming->len != (int)sizeof(payload) ||
        memcmp(incoming->data, payload, sizeof(payload)) != 0) {
        fprintf(stderr, "UDP loopback payload was not received intact\n");
        goto cleanup;
    }

    status = 0;

cleanup:
    SDLNet_FreePacket(incoming);
    SDLNet_FreePacket(outgoing);
    SDLNet_UDP_Close(sender);
    SDLNet_UDP_Close(receiver);
    test_runtime_quit();
    return status;
}
