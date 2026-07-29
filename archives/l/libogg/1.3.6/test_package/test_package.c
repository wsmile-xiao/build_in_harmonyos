#include <ogg/ogg.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    static const unsigned char payload[] = "OpenHarmony Ogg packet";
    ogg_packet packet = {0};
    ogg_page page = {0};
    ogg_stream_state encoder;
    ogg_stream_state decoder;

    if (ogg_stream_init(&encoder, 0x4f484f53) != 0) {
        return 1;
    }
    packet.packet = (unsigned char *)payload;
    packet.bytes = (long)strlen((const char *)payload);
    packet.b_o_s = 1;
    packet.e_o_s = 1;
    if (ogg_stream_packetin(&encoder, &packet) != 0 ||
        ogg_stream_flush(&encoder, &page) != 1) {
        ogg_stream_clear(&encoder);
        return 2;
    }
    if (ogg_stream_init(&decoder, ogg_page_serialno(&page)) != 0) {
        ogg_stream_clear(&encoder);
        return 3;
    }
    if (ogg_stream_pagein(&decoder, &page) != 0 ||
        ogg_stream_packetout(&decoder, &packet) != 1) {
        ogg_stream_clear(&decoder);
        ogg_stream_clear(&encoder);
        return 3;
    }
    if (packet.bytes != (long)strlen((const char *)payload) ||
        memcmp(packet.packet, payload, (size_t)packet.bytes) != 0) {
        ogg_stream_clear(&decoder);
        ogg_stream_clear(&encoder);
        return 4;
    }
    ogg_stream_clear(&decoder);
    ogg_stream_clear(&encoder);
    puts("libogg installed-package round trip passed");
    return 0;
}
