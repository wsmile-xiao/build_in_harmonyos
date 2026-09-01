#include "test_common.h"

#include <string.h>

int main(void)
{
    static const char payload[] = "socket-set-ready";
    UDPsocket sender = NULL;
    UDPsocket receiver = NULL;
    UDPpacket *outgoing = NULL;
    UDPpacket *incoming = NULL;
    SDLNet_SocketSet set = NULL;
    IPaddress target;
    int added = 0;
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

    set = SDLNet_AllocSocketSet(1);
    outgoing = SDLNet_AllocPacket((int)sizeof(payload));
    incoming = SDLNet_AllocPacket(128);
    if (set == NULL || outgoing == NULL || incoming == NULL) {
        test_report_net_error("socket-set allocation");
        goto cleanup;
    }
    if (SDLNet_UDP_AddSocket(set, receiver) != 1) {
        test_report_net_error("SDLNet_UDP_AddSocket");
        goto cleanup;
    }
    added = 1;

    memcpy(outgoing->data, payload, sizeof(payload));
    outgoing->len = (int)sizeof(payload);
    outgoing->address = target;
    if (SDLNet_UDP_Send(sender, -1, outgoing) != 1) {
        test_report_net_error("SDLNet_UDP_Send");
        goto cleanup;
    }
    if (SDLNet_CheckSockets(set, 2000) != 1 ||
        !SDLNet_SocketReady(receiver)) {
        test_report_net_error("SDLNet_CheckSockets");
        goto cleanup;
    }
    if (SDLNet_UDP_Recv(receiver, incoming) != 1 ||
        incoming->len != (int)sizeof(payload) ||
        memcmp(incoming->data, payload, sizeof(payload)) != 0) {
        fprintf(stderr, "Ready UDP socket did not yield the expected payload\n");
        goto cleanup;
    }
    if (SDLNet_UDP_DelSocket(set, receiver) != 0) {
        test_report_net_error("SDLNet_UDP_DelSocket");
        goto cleanup;
    }
    added = 0;

    status = 0;

cleanup:
    if (added) {
        SDLNet_UDP_DelSocket(set, receiver);
    }
    SDLNet_FreeSocketSet(set);
    SDLNet_FreePacket(incoming);
    SDLNet_FreePacket(outgoing);
    SDLNet_UDP_Close(sender);
    SDLNet_UDP_Close(receiver);
    test_runtime_quit();
    return status;
}
