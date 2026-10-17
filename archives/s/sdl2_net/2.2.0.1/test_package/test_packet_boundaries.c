#include "test_common.h"

int main(void)
{
    UDPpacket *packet = NULL;
    UDPpacket **packets = NULL;
    int status = 1;
    int index;

    if (test_runtime_init() < 0) {
        return 1;
    }

    packet = SDLNet_AllocPacket(1);
    if (packet == NULL || packet->data == NULL || packet->maxlen != 1) {
        test_report_net_error("SDLNet_AllocPacket(1)");
        goto cleanup;
    }
    packet->data[0] = 0xa5u;
    packet->len = 1;

    if (SDLNet_ResizePacket(packet, 65535) != 65535 ||
        packet->data == NULL || packet->maxlen != 65535) {
        test_report_net_error("SDLNet_ResizePacket(65535)");
        goto cleanup;
    }

    packets = SDLNet_AllocPacketV(3, 32);
    if (packets == NULL || packets[3] != NULL) {
        test_report_net_error("SDLNet_AllocPacketV");
        goto cleanup;
    }
    for (index = 0; index < 3; ++index) {
        if (packets[index] == NULL || packets[index]->data == NULL ||
            packets[index]->maxlen != 32) {
            fprintf(stderr, "Packet vector allocation is incomplete\n");
            goto cleanup;
        }
        packets[index]->data[0] = (Uint8)index;
        packets[index]->len = 1;
    }

    status = 0;

cleanup:
    SDLNet_FreePacketV(packets);
    SDLNet_FreePacket(packet);
    test_runtime_quit();
    return status;
}
