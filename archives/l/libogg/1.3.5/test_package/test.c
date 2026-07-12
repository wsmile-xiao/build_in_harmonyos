#include <stdio.h>
#include <string.h>
#include <ogg/ogg.h>

int main(void) {
    /* R34: test ogg stream round-trip */
    ogg_stream_state os;
    if (ogg_stream_init(&os, 0) != 0) {
        printf("FAIL: ogg_stream_init\n");
        return 1;
    }

    ogg_packet op;
    op.packet = (unsigned char *)"Hello, HarmonyOS!";
    op.bytes = strlen((const char *)op.packet);
    op.b_o_s = 1;
    op.e_o_s = 0;
    op.granulepos = 0;
    op.packetno = 0;

    if (ogg_stream_packetin(&os, &op) != 0) {
        printf("FAIL: ogg_stream_packetin\n");
        ogg_stream_clear(&os);
        return 1;
    }

    ogg_page og;
    if (ogg_stream_pageout(&os, &og) == 0) {
        printf("FAIL: ogg_stream_pageout\n");
        ogg_stream_clear(&os);
        return 1;
    }

    ogg_stream_clear(&os);
    printf("PASS: ogg stream init+packetin+pageout round-trip OK\n");
    return 0;
}
