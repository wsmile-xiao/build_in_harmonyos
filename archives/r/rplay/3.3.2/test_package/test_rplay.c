#include <rplay.h>
#include <stdio.h>

int main(void) {
    RPLAY *packet = rplay_create(RPLAY_PING);
    if (!packet) return 1;
    if (packet->command != RPLAY_PING) return 2;
    if (rplay_pack(packet) < 0) return 3;
    if ((unsigned char)packet->buf[0] != RPLAY_PACKET_ID) return 4;
    rplay_destroy(packet);
    puts("RPLAY_CONSUMER_PASS");
    return 0;
}
