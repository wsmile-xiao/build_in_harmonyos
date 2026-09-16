#include <ogg/ogg.h>

#include <stdio.h>
#include <string.h>

/* Installed-package round trip for libogg: encode one packet, flush it to
 * an Ogg page, submit the page to a second stream, and verify the recovered
 * packet is byte-identical. Each stage prints one "CHECK n OK" line and the
 * program exits non-zero at the first failing stage, so exit 0 together with
 * the four log lines proves the whole flow. The four stages share one
 * process fate and are counted as a single integration flow (not split into
 * cases), the same accounting as libogg/1.3.6.1.
 */
int main(void)
{
    static const unsigned char payload[] = "OpenHarmony Ogg packet";
    ogg_packet packet = {0};
    ogg_page page = {0};
    ogg_stream_state encoder;
    ogg_stream_state decoder;

    if (ogg_stream_init(&encoder, 0x4f484f53) != 0) {
        printf("CHECK 1 FAILED: ogg_stream_init (encoder)\n");
        return 1;
    }
    printf("CHECK 1 OK: ogg_stream_init (encoder)\n");

    packet.packet = (unsigned char *)payload;
    packet.bytes = (long)strlen((const char *)payload);
    packet.b_o_s = 1;
    packet.e_o_s = 1;
    if (ogg_stream_packetin(&encoder, &packet) != 0 ||
        ogg_stream_flush(&encoder, &page) != 1) {
        printf("CHECK 2 FAILED: ogg_stream_packetin + ogg_stream_flush\n");
        ogg_stream_clear(&encoder);
        return 2;
    }
    printf("CHECK 2 OK: ogg_stream_packetin + ogg_stream_flush\n");

    if (ogg_stream_init(&decoder, ogg_page_serialno(&page)) != 0) {
        printf("CHECK 3 FAILED: ogg_stream_init (decoder)\n");
        ogg_stream_clear(&encoder);
        return 3;
    }
    if (ogg_stream_pagein(&decoder, &page) != 0 ||
        ogg_stream_packetout(&decoder, &packet) != 1) {
        printf("CHECK 3 FAILED: ogg_stream_pagein + ogg_stream_packetout\n");
        ogg_stream_clear(&decoder);
        ogg_stream_clear(&encoder);
        return 3;
    }
    printf("CHECK 3 OK: ogg_stream_pagein + ogg_stream_packetout\n");

    if (packet.bytes != (long)strlen((const char *)payload) ||
        memcmp(packet.packet, payload, (size_t)packet.bytes) != 0) {
        printf("CHECK 4 FAILED: payload mismatch after round trip\n");
        ogg_stream_clear(&decoder);
        ogg_stream_clear(&encoder);
        return 4;
    }
    printf("CHECK 4 OK: payload round-trip identical (%ld bytes)\n", (long)packet.bytes);

    ogg_stream_clear(&decoder);
    ogg_stream_clear(&encoder);
    puts("libogg installed-package round trip passed (4/4 stage lines)");
    return 0;
}
