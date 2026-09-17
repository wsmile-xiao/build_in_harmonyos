/* Installed-package consumer test for ogg 1.1.1.
 *
 * Exercises the installed library through its public <ogg/ogg.h> API: builds
 * an Ogg stream, encodes one packet into a page (ogg_stream_packetin +
 * ogg_stream_flush), then decodes it back through a second stream state
 * (ogg_stream_pagein + ogg_stream_packetout) and verifies the payload
 * round-trips byte-for-byte. Mirrors the upstream test_framing semantics
 * against the *installed* package (not the build tree).
 */
#include <ogg/ogg.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    static const unsigned char payload[] = "OpenHarmony ogg 1.1.1 packet";
    ogg_packet packet;
    ogg_page page;
    ogg_stream_state encoder;
    ogg_stream_state decoder;

    if (ogg_stream_init(&encoder, 0x4f484f53) != 0) {
        fprintf(stderr, "ogg_stream_init(encoder) failed\n");
        return 1;
    }
    memset(&packet, 0, sizeof(packet));
    memset(&page, 0, sizeof(page));
    packet.packet = (unsigned char *)payload;
    packet.bytes = (long)strlen((const char *)payload);
    packet.b_o_s = 1;
    packet.e_o_s = 1;
    if (ogg_stream_packetin(&encoder, &packet) != 0 ||
        ogg_stream_flush(&encoder, &page) != 1) {
        fprintf(stderr, "ogg_stream_packetin/flush failed\n");
        ogg_stream_clear(&encoder);
        return 2;
    }
    if (ogg_stream_init(&decoder, ogg_page_serialno(&page)) != 0) {
        fprintf(stderr, "ogg_stream_init(decoder) failed\n");
        ogg_stream_clear(&encoder);
        return 3;
    }
    if (ogg_stream_pagein(&decoder, &page) != 0 ||
        ogg_stream_packetout(&decoder, &packet) != 1) {
        fprintf(stderr, "ogg_stream_pagein/packetout failed\n");
        ogg_stream_clear(&decoder);
        ogg_stream_clear(&encoder);
        return 4;
    }
    if (packet.bytes != (long)strlen((const char *)payload) ||
        memcmp(packet.packet, payload, (size_t)packet.bytes) != 0) {
        fprintf(stderr, "payload round trip mismatch\n");
        ogg_stream_clear(&decoder);
        ogg_stream_clear(&encoder);
        return 5;
    }
    ogg_stream_clear(&decoder);
    ogg_stream_clear(&encoder);
    puts("ogg 1.1.1 installed-package round trip passed");
    return 0;
}
