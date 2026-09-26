/*
 * test_package/test.c — 消费者视角真实调用 libtiff API（R34，禁止空壳）。
 *
 * 真实读写断言：用 TIFFWriteEncodedStrip 以各 COMPRESSION_* 后端写一张小图，
 * 再用 TIFFReadEncodedStrip 读回比对像素。覆盖后端：
 *   COMPRESSION_NONE、COMPRESSION_LZW、COMPRESSION_DEFLATE(zlib)、
 *   COMPRESSION_ADOBE_DEFLATE、COMPRESSION_JPEG(libjpeg-turbo)、
 *   COMPRESSION_ZSTD、COMPRESSION_LZMA、COMPRESSION_WEBP、COMPRESSION_LERC、
 *   COMPRESSION_JBIG。
 * 注：libdeflate 作为 DEFLATE 的加速后端由 libtiff 内部择优，不必单独枚举。
 *
 * 上游约束（libtiff 官方测试同样遵守）：
 *   - WEBP 编码器只支持 3(RGB)/4(RGBA) bands（"WEBP driver doesn't support 1 bands"）；
 *   - JBIG 只实现了 strip（TIFFWriteEncodedStrip）编码，无 scanline 编码
 *     （"ISO JBIG scanline encoding is not implemented"）；
 *   - JPEG/WEBP 是有损压缩，比对采用容差（maxdiff 阈值）而非逐字节相等。
 */
#include <tiffio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define W 32
#define H 16

typedef struct {
    int comp;
    const char *name;
    int spp;            /* samples per pixel */
    int photometric;
    int quality;        /* jpeg quality / webp quality（有损时） */
    int maxdiff;        /* 0=逐字节相等；>0=有损容差 */
    int bits;           /* bits per sample（0=8） */
} codec_t;

static const codec_t codecs[] = {
    { COMPRESSION_NONE,          "none",          1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_LZW,           "lzw",           1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_DEFLATE,       "zlib(deflate)", 1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_ADOBE_DEFLATE, "adobe-deflate", 1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_JPEG,          "jpeg",          1, PHOTOMETRIC_MINISBLACK, 90, 24, 0 },
    { COMPRESSION_ZSTD,          "zstd",          1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_LZMA,          "lzma",          1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_WEBP,          "webp",          3, PHOTOMETRIC_RGB,        100, 8, 0 },
    { COMPRESSION_LERC,          "lerc",          1, PHOTOMETRIC_MINISBLACK, 0,  0, 0 },
    { COMPRESSION_JBIG,          "jbig",          1, PHOTOMETRIC_MINISBLACK, 0,  0, 1 },
};

#define STRIP_BYTES (W * H)   /* 单 strip：整图（单平面） */

static int roundtrip(const codec_t *c) {
    char fn[64];
    snprintf(fn, sizeof(fn), "t_%s.tif", c->name);
    int bps = c->bits ? c->bits : 8;
    size_t npix = (size_t)W * H * c->spp;
    size_t nbytes = npix * bps / 8;
    unsigned char *src = malloc(nbytes), *dst = calloc(1, nbytes);
    if (!src || !dst) return 1;
    for (size_t i = 0; i < nbytes; i++)
        src[i] = (unsigned char)((i * 7 + i / W * 13) & (bps == 1 ? 0xff : 0xff));

    TIFF *out = TIFFOpen(fn, "w");
    if (!out) { fprintf(stderr, "FAIL[%s]: TIFFOpen(w)\n", c->name); return 1; }
    TIFFSetField(out, TIFFTAG_IMAGEWIDTH, W);
    TIFFSetField(out, TIFFTAG_IMAGELENGTH, H);
    TIFFSetField(out, TIFFTAG_SAMPLESPERPIXEL, c->spp);
    TIFFSetField(out, TIFFTAG_BITSPERSAMPLE, bps);
    TIFFSetField(out, TIFFTAG_ROWSPERSTRIP, H);
    TIFFSetField(out, TIFFTAG_COMPRESSION, c->comp);
    TIFFSetField(out, TIFFTAG_PHOTOMETRIC, c->photometric);
    TIFFSetField(out, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
    if (c->comp == COMPRESSION_JPEG)
        TIFFSetField(out, TIFFTAG_JPEGQUALITY, c->quality);
    if (c->comp == COMPRESSION_WEBP)
        /* WEBP 无损模式：libwebp 编码器质量/分块实现下有损回读偏差大
         *（实测 maxdiff=209），上游官方测试同样用 lossless 模式（rgb3x2）。 */
        TIFFSetField(out, TIFFTAG_WEBP_LOSSLESS, 1);
    tstrip_t strip = 0;
    if (TIFFWriteEncodedStrip(out, strip, src, (tmsize_t)nbytes) < 0) {
        fprintf(stderr, "FAIL[%s]: TIFFWriteEncodedStrip\n", c->name);
        TIFFClose(out); return 1;
    }
    TIFFClose(out);

    TIFF *in = TIFFOpen(fn, "r");
    if (!in) { fprintf(stderr, "FAIL[%s]: TIFFOpen(r)\n", c->name); return 1; }
    uint16_t got_comp = 0;
    TIFFGetField(in, TIFFTAG_COMPRESSION, &got_comp);
    if ((int)got_comp != c->comp) {
        fprintf(stderr, "FAIL[%s]: readback compression %u != %d\n", c->name, got_comp, c->comp);
        TIFFClose(in); return 1;
    }
    tmsize_t n = TIFFReadEncodedStrip(in, strip, dst, (tmsize_t)nbytes);
    if (n < 0) {
        fprintf(stderr, "FAIL[%s]: TIFFReadEncodedStrip\n", c->name);
        TIFFClose(in); return 1;
    }
    TIFFClose(in);

    int maxd = 0;
    for (size_t i = 0; i < nbytes; i++) {
        int d = src[i] > dst[i] ? src[i] - dst[i] : dst[i] - src[i];
        if (d > maxd) maxd = d;
    }
    if (maxd > c->maxdiff) {
        fprintf(stderr, "FAIL[%s]: pixel mismatch maxdiff=%d > tol=%d\n",
                c->name, maxd, c->maxdiff);
        return 1;
    }
    remove(fn);
    printf("PASS[%s]: write+read roundtrip OK (maxdiff=%d, tol=%d, %u bytes)\n",
           c->name, maxd, c->maxdiff, (unsigned)n);
    free(src); free(dst);
    return 0;
}

int main(void) {
    int fails = 0, n = (int)(sizeof(codecs) / sizeof(codecs[0]));
    for (int i = 0; i < n; i++)
        fails += roundtrip(&codecs[i]);
    if (fails) {
        fprintf(stderr, "FAIL: %d backend(s) failed\n", fails);
        return 1;
    }
    printf("libtiff version: %s\n", TIFFGetVersion());
    printf("PASS: all %d codec backends roundtrip OK\n", n);
    return 0;
}
