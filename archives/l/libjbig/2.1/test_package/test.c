/* test.c — real consumer test source for libjbig 2.1 (L0c).
 *
 * Links against libjbig.a and verifies the JBIG1 encoder round-trips:
 * encode a 16x16 image (data_out callback collects output), then decode
 * with jbg_dec_in/jbg_dec_getimage and check dimensions match.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "jbig.h"

#define W 16
#define H 16

static unsigned char enc_buf[8192];
static unsigned long enc_len = 0;

static void out_cb(unsigned char *start, size_t len, void *file) {
    (void)file;
    if (enc_len + len <= sizeof(enc_buf)) {
        memcpy(enc_buf + enc_len, start, len);
        enc_len += (unsigned long)len;
    }
}

int main(void) {
    struct jbg_enc_state e;
    struct jbg_dec_state d;
    unsigned char img[W * H];
    unsigned char *planes[1];
    size_t cnt = 0;
    int i;

    for (i = 0; i < W * H; i++)
        img[i] = (unsigned char)((i * 7) % 256 > 128 ? 1 : 0);
    planes[0] = img;

    jbg_enc_init(&e, W, H, 1, planes, out_cb, NULL);
    jbg_enc_layers(&e, 0);
    jbg_enc_lrange(&e, 0, 2);
    jbg_enc_options(&e, 0, JBG_TPDON | JBG_TPBON | JBG_DPON, 0, 0, 0);
    jbg_enc_out(&e);
    jbg_enc_free(&e);
    if (enc_len == 0) {
        printf("FAIL: encode produced no output\n");
        return 1;
    }

    jbg_dec_init(&d);
    if (jbg_dec_in(&d, enc_buf, enc_len, &cnt) != JBG_EOK) {
        printf("FAIL: jbg_dec_in\n");
        jbg_dec_free(&d);
        return 1;
    }
    if (jbg_dec_getwidth(&d) != W || jbg_dec_getheight(&d) != H) {
        printf("FAIL: decoded dims %lux%lu, expected %dx%d\n",
               jbg_dec_getwidth(&d), jbg_dec_getheight(&d), W, H);
        jbg_dec_free(&d);
        return 1;
    }
    if (jbg_dec_getimage(&d, 0) == NULL) {
        printf("FAIL: no decoded image\n");
        jbg_dec_free(&d);
        return 1;
    }
    jbg_dec_free(&d);

    printf("OK: libjbig 2.1 encode/decode round-trip (%dx%d, %lu bytes)\n",
           W, H, enc_len);
    return 0;
}
