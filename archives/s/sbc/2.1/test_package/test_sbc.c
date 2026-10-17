/* Consumer test for sbc/2.1 on OHOS PC.
 *
 * Verifies the delivered libsbc through a real codec round trip with the
 * public sbc API: configure a 44.1 kHz stereo SBC stream, size the input
 * with sbc_get_codesize(), encode one frame, decode it back, and require
 * the decoded byte count to equal the codesize exactly.  Exit code is
 * the verdict.
 */
#include <sbc/sbc.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int failures = 0;
    sbc_t enc;
    sbc_t dec;
    unsigned char *pcm;
    unsigned char *encbuf;
    unsigned char *back;
    size_t codesize;
    size_t encoded = 0;
    ssize_t written;

    memset(&enc, 0, sizeof enc);
    memset(&dec, 0, sizeof dec);

    if (sbc_init(&enc, 0) != 0 || sbc_init(&dec, 0) != 0) {
        puts("sbc_init failed");
        return 1;
    }
    enc.frequency = SBC_FREQ_44100;
    enc.blocks = SBC_BLK_8;
    enc.subbands = SBC_SB_8;
    enc.mode = SBC_MODE_STEREO;
    enc.allocation = SBC_AM_LOUDNESS;
    enc.bitpool = 53;
    dec.frequency = SBC_FREQ_44100;

    codesize = sbc_get_codesize(&enc);
    pcm = malloc(codesize);
    encbuf = malloc(codesize * 2);
    back = malloc(codesize);
    if (!pcm || !encbuf || !back) { puts("alloc failed"); return 1; }
    for (size_t i = 0; i < codesize / 2; ++i) {
        unsigned v = (unsigned)(i * 2517) % 65536;
        pcm[2 * i] = (unsigned char)(v >> 8);
        pcm[2 * i + 1] = (unsigned char)(v & 0xff);
    }

    written = sbc_encode(&enc, pcm, codesize, encbuf, codesize * 2, &encoded);
    printf("sbc_encode: written=%zd bytes encoded=%zu\n",
           written, encoded);
    if (written != (ssize_t)codesize) {
        printf("FAIL: sbc_encode consumed %zd of %zu bytes\n",
               written, codesize);
        ++failures;
    }
    if (encoded == 0) {
        puts("FAIL: no encoded bytes produced");
        ++failures;
    }

    size_t written_total = 0;
    size_t offset = 0;
    /* sbc_decode returns the number of CONSUMED input bytes; the decoded
     * PCM byte count comes back through the `written` out-param. */
    while (offset < encoded) {
        size_t pcm_bytes = 0;
        ssize_t consumed = sbc_decode(&dec, encbuf + offset, encoded - offset,
                                      back + written_total,
                                      codesize - written_total, &pcm_bytes);
        if (consumed <= 0) {
            puts("FAIL: sbc_decode consumed nothing");
            ++failures;
            break;
        }
        written_total += pcm_bytes;
        offset += consumed;
    }
    if (written_total != codesize) {
        printf("FAIL: decoded %zu bytes, expected %zu\n",
               written_total, codesize);
        ++failures;
    } else {
        printf("round trip decoded %zu bytes: OK\n", written_total);
    }

    free(pcm); free(encbuf); free(back);
    sbc_finish(&enc);
    sbc_finish(&dec);
    return failures ? 1 : 0;
}
