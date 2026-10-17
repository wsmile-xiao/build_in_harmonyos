#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "cobs.h"
#include "cobsr.h"

/* 消费者测试：通过公开 API cobs_encode/cobs_decode 验证编解码闭环。 */
int main(void) {
    const uint8_t src[] = { 'H', 'e', 'l', 'l', 'o', 0, 'c', 'o', 'b', 's' };
    uint8_t enc[64], dec[64];
    cobs_encode_result er;
    cobs_decode_result dr;

    memset(enc, 0, sizeof(enc));
    memset(dec, 0, sizeof(dec));

    er = cobs_encode(enc, sizeof(enc), src, sizeof(src));
    if (er.status != COBS_ENCODE_OK || er.out_len == 0) {
        printf("cobs_encode FAILED (status=%d out_len=%zu)\n", er.status, er.out_len);
        return 1;
    }

    dr = cobs_decode(dec, sizeof(dec), enc, er.out_len);
    if (dr.status != COBS_DECODE_OK) {
        printf("cobs_decode FAILED (status=%d)\n", dr.status);
        return 1;
    }
    if (dr.out_len != sizeof(src) || memcmp(dec, src, sizeof(src)) != 0) {
        printf("cobs round-trip MISMATCH (decoded=%zu expected=%zu)\n",
               dr.out_len, sizeof(src));
        return 1;
    }

    /* COBS/R 变体闭环 */
    memset(enc, 0, sizeof(enc));
    memset(dec, 0, sizeof(dec));
    cobsr_encode_result rer = cobsr_encode(enc, sizeof(enc), src, sizeof(src));
    if (rer.status != COBSR_ENCODE_OK) {
        printf("cobsr_encode FAILED (status=%d)\n", rer.status);
        return 1;
    }
    cobsr_decode_result rdr = cobsr_decode(dec, sizeof(dec), enc, rer.out_len);
    if (rdr.status != COBSR_DECODE_OK || rdr.out_len != sizeof(src)
        || memcmp(dec, src, sizeof(src)) != 0) {
        printf("cobsr round-trip MISMATCH (status=%d decoded=%zu expected=%zu)\n",
               rdr.status, rdr.out_len, sizeof(src));
        return 1;
    }

    printf("cobs-c 0.4 consumer test: OK (cobs + cobsr round-trip passed, %zu bytes)\n",
           sizeof(src));
    return 0;
}
