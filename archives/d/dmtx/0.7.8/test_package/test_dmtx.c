/* dmtx (libdmtx) consumer test (R34): real encode→decode roundtrip —
 * the upstream test/simple_test pattern (dmtxEncodeCreate →
 * dmtxEncodeDataMatrix → dmtxImageCreate → dmtxDecodeCreate →
 * dmtxRegionFindNext → dmtxDecodeMatrixRegion), asserting the decoded
 * output equals the input string. */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <dmtx.h>

int main(void) {
    unsigned char str[] = "30Q324343430794<OQQ";
    unsigned char *pxl;
    DmtxEncode *enc;
    DmtxImage *img;
    DmtxDecode *dec;
    DmtxRegion *reg;
    DmtxMessage *msg;
    size_t width, height, bpp;

    /* 1) ENCODE */
    enc = dmtxEncodeCreate();
    if (!enc) { fprintf(stderr, "FAIL: dmtxEncodeCreate\n"); return 1; }
    if (dmtxEncodeDataMatrix(enc, strlen((const char *)str), str) != DmtxPass) {
        fprintf(stderr, "FAIL: dmtxEncodeDataMatrix\n"); return 1;
    }

    /* 2) COPY image data before releasing encoding memory */
    width = dmtxImageGetProp(enc->image, DmtxPropWidth);
    height = dmtxImageGetProp(enc->image, DmtxPropHeight);
    bpp = dmtxImageGetProp(enc->image, DmtxPropBytesPerPixel);
    pxl = (unsigned char *)malloc(width * height * bpp);
    if (!pxl) { fprintf(stderr, "FAIL: malloc\n"); return 1; }
    memcpy(pxl, enc->image->pxl, width * height * bpp);
    dmtxEncodeDestroy(&enc);

    /* 3) DECODE */
    img = dmtxImageCreate(pxl, width, height, DmtxPack24bppRGB);
    if (!img) { fprintf(stderr, "FAIL: dmtxImageCreate\n"); return 1; }
    dec = dmtxDecodeCreate(img, 1);
    if (!dec) { fprintf(stderr, "FAIL: dmtxDecodeCreate\n"); return 1; }
    reg = dmtxRegionFindNext(dec, NULL);
    if (!reg) { fprintf(stderr, "FAIL: dmtxRegionFindNext (no region found)\n"); return 1; }
    msg = dmtxDecodeMatrixRegion(dec, reg, DmtxUndefined);
    if (!msg) { fprintf(stderr, "FAIL: dmtxDecodeMatrixRegion\n"); return 1; }

    /* 4) ROUNDTRIP assert */
    if (msg->outputIdx != strlen((const char *)str) ||
        memcmp(msg->output, str, msg->outputIdx) != 0) {
        fprintf(stderr, "FAIL: roundtrip mismatch\n");
        return 1;
    }
    printf("OK: dmtx roundtrip %zux%zu bpp=%zu -> \"%.*s\"\n",
           width, height, bpp, (int)msg->outputIdx, msg->output);

    dmtxMessageDestroy(&msg);
    dmtxRegionDestroy(&reg);
    dmtxDecodeDestroy(&dec);
    dmtxImageDestroy(&img);
    free(pxl);
    return 0;
}
